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
) -> dict[str, object]:
    _validate_prompt_server(prompt_server)
    execution_module = _get_execution_module()
    if execution_module is None:
        raise RuntimeError("RookieUI host execution module is unavailable.")

    number = getattr(prompt_server, "number", 0)
    setattr(prompt_server, "number", number + 1)
    prompt_id = str(uuid.uuid4())

    node_replace_manager = getattr(prompt_server, "node_replace_manager", None)
    if node_replace_manager is not None and hasattr(node_replace_manager, "apply_replacements"):
        node_replace_manager.apply_replacements(workflow)

    valid = await execution_module.validate_prompt(prompt_id, workflow, None)
    if not valid[0]:
        raise ValueError(valid[1])

    extra_data: dict[str, object] = {
        "create_time": int(time.time() * 1000),
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

    outputs_to_execute = valid[2]
    node_errors = valid[3]
    prompt_server.prompt_queue.put(
        (number, prompt_id, workflow, extra_data, outputs_to_execute, {})
    )
    return {
        "accepted": True,
        "prompt_id": prompt_id,
        "number": number,
        "node_errors": node_errors,
    }
