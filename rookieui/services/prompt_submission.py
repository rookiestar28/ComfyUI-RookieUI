from __future__ import annotations

import time
import uuid
from typing import Any


ROOKIEUI_COMFY_USAGE_SOURCE = "comfyui-rookieui"


def _get_execution_module() -> Any:
    try:
        import execution
    except ImportError:
        return None
    return execution


def _validate_prompt_server(prompt_server: Any) -> None:
    if prompt_server is None:
        raise RuntimeError("RookieUI host prompt server is unavailable.")
    if not hasattr(prompt_server, "prompt_queue"):
        raise RuntimeError("RookieUI host prompt queue is unavailable.")
    if not hasattr(prompt_server.prompt_queue, "put"):
        raise RuntimeError("RookieUI host prompt queue cannot accept prompts.")
    if not hasattr(prompt_server, "trigger_on_prompt"):
        raise RuntimeError("RookieUI host prompt hooks are unavailable.")


def _resolve_prompt_id(value: object) -> str:
    if value is None:
        return str(uuid.uuid4())
    if not isinstance(value, str):
        raise ValueError(f"prompt_id must be a string, got {type(value).__name__}")
    try:
        normalized = str(uuid.UUID(value))
    except (AttributeError, ValueError) as exc:
        raise ValueError("prompt_id must be a UUID in canonical lowercase hyphenated form") from exc
    if normalized != value:
        raise ValueError("prompt_id must be a UUID in canonical lowercase hyphenated form")
    return value


async def submit_prompt_workflow(
    prompt_server: Any,
    workflow: dict[str, object],
    *,
    client_id: str | None = None,
    origin: str = "rookieui",
    surface: str = "txt2img",
    profile: str | None = None,
    extra_pnginfo: dict[str, object] | None = None,
    extra_metadata: dict[str, object] | None = None,
    number: int | float | None = None,
    front: bool = False,
    prompt_id: str | None = None,
    partial_execution_targets: list[str] | None = None,
) -> dict[str, object]:
    _validate_prompt_server(prompt_server)
    execution_module = _get_execution_module()
    if execution_module is None:
        raise RuntimeError("RookieUI host execution module is unavailable.")

    extra_data: dict[str, object] = {
        # CRITICAL: RookieUI queue/history filtering must rely on explicit internal metadata, not prompt text or display labels.
        "rookieui_origin": origin,
        "rookieui_surface": surface,
        # CRITICAL: ComfyUI defaults --preview-method to none; forcing auto keeps live-preview websocket frames available for RookieUI runtime panels.
        "preview_method": "auto",
    }
    if profile:
        extra_data["rookieui_profile"] = profile
    if client_id:
        extra_data["client_id"] = client_id
    if isinstance(extra_metadata, dict):
        # IMPORTANT: feature-specific queue metadata must merge here rather than piggybacking on prompt text; queue/history reconstruction depends on explicit internal tags.
        extra_data.update(extra_metadata)
    # IMPORTANT: direct queue submissions bypass ComfyUI's /prompt header fallback; keep host API-node usage attribution stable.
    extra_data["comfy_usage_source"] = ROOKIEUI_COMFY_USAGE_SOURCE
    if isinstance(extra_pnginfo, dict) and extra_pnginfo:
        # CRITICAL: keep embeddable PNG metadata separate from queue-only tags; mixing them caused generated files to lose reproducible parameters.
        extra_data["extra_pnginfo"] = extra_pnginfo

    envelope: dict[str, object] = {
        "prompt": workflow,
        "extra_data": extra_data,
    }
    if client_id:
        envelope["client_id"] = client_id
    if number is not None:
        envelope["number"] = number
    if front:
        envelope["front"] = True
    if prompt_id is not None:
        envelope["prompt_id"] = prompt_id
    if partial_execution_targets is not None:
        envelope["partial_execution_targets"] = partial_execution_targets

    # IMPORTANT: host on-prompt handlers may replace the entire envelope and
    # mutate graph inputs before replacement and validation.
    envelope = prompt_server.trigger_on_prompt(envelope)
    if not isinstance(envelope, dict):
        raise ValueError("Host prompt hooks returned an invalid prompt envelope.")

    if "number" in envelope:
        resolved_number: int | float = float(envelope["number"])
    else:
        resolved_number = getattr(prompt_server, "number", 0)
        if envelope.get("front"):
            resolved_number = -resolved_number
        setattr(prompt_server, "number", getattr(prompt_server, "number", 0) + 1)

    resolved_prompt_id = _resolve_prompt_id(envelope.get("prompt_id"))
    resolved_workflow = envelope.get("prompt")
    if not isinstance(resolved_workflow, dict):
        raise ValueError("Host prompt hooks returned an invalid prompt graph.")
    resolved_partial_targets = envelope.get("partial_execution_targets")

    node_replace_manager = getattr(prompt_server, "node_replace_manager", None)
    if node_replace_manager is not None and hasattr(node_replace_manager, "apply_replacements"):
        node_replace_manager.apply_replacements(resolved_workflow)

    valid = await execution_module.validate_prompt(
        resolved_prompt_id,
        resolved_workflow,
        resolved_partial_targets,
    )
    if not valid[0]:
        raise ValueError(valid[1])

    resolved_extra_data = envelope.get("extra_data")
    if not isinstance(resolved_extra_data, dict):
        resolved_extra_data = {}
    resolved_extra_data.setdefault("rookieui_origin", origin)
    resolved_extra_data.setdefault("rookieui_surface", surface)
    resolved_extra_data.setdefault("preview_method", "auto")
    if profile:
        resolved_extra_data.setdefault("rookieui_profile", profile)
    resolved_client_id = envelope.get("client_id")
    if isinstance(resolved_client_id, str) and resolved_client_id:
        resolved_extra_data["client_id"] = resolved_client_id
    # Direct submission has no request header fallback; retain explicit API-node attribution.
    resolved_extra_data["comfy_usage_source"] = ROOKIEUI_COMFY_USAGE_SOURCE

    sensitive: dict[str, object] = {}
    for sensitive_key in getattr(execution_module, "SENSITIVE_EXTRA_DATA_KEYS", ()):
        if sensitive_key in resolved_extra_data:
            sensitive[sensitive_key] = resolved_extra_data.pop(sensitive_key)
    resolved_extra_data["create_time"] = int(time.time() * 1000)

    outputs_to_execute = valid[2]
    node_errors = valid[3]
    prompt_server.prompt_queue.put(
        (
            resolved_number,
            resolved_prompt_id,
            resolved_workflow,
            resolved_extra_data,
            outputs_to_execute,
            sensitive,
        )
    )
    return {
        "accepted": True,
        "prompt_id": resolved_prompt_id,
        "number": resolved_number,
        "node_errors": node_errors,
    }
