from __future__ import annotations

import asyncio
import inspect
from dataclasses import asdict, dataclass
from typing import Any

from rookieui.contracts.prompt_workbench import (
    PROMPT_WORKBENCH_DANBOORU_ACTION_ID,
    PROMPT_WORKBENCH_DANBOORU_NODE_ALIASES,
    PROMPT_WORKBENCH_DANBOORU_ROUTE_PATH,
    build_default_prompt_workbench_host_actions,
    build_prompt_workbench_contract_meta,
)

_MAX_PROMPT_LENGTH = 16000
_MAX_OPTIONAL_TEXT_LENGTH = 4000
_DEFAULT_NODE_INPUTS = {
    "model_name": "dart-v1-sft",
    "tag_length": "long",
    "seed": 0,
    "temperature": 1.0,
    "top_k": 30,
    "top_p": 1.0,
    "num_beams": 1,
    "model_device": "auto",
    "model_backend": "ONNX (Quantized)",
    "max_new_tokens": 128,
    "cfg_scale": 1.5,
    "debug_logging": False,
}


class PromptWorkbenchDanbooruHostUnavailableError(RuntimeError):
    pass


class PromptWorkbenchDanbooruExecutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class PromptWorkbenchDanbooruExecutionResult:
    action_id: str
    final_prompt: str
    generated_suffix: str
    host_node_alias: str
    availability: dict[str, Any]
    warnings: list[str]
    warning_codes: list[str]

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["contract"] = build_prompt_workbench_contract_meta(surface="prompt_tools_upsample")
        return payload


def _normalize_text(value: object, *, max_length: int) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()[:max_length]


def _normalize_request_payload(payload: object) -> dict[str, str]:
    if not isinstance(payload, dict):
        raise ValueError("Prompt-workbench Danbooru upsample payload must be an object.")
    prompt = _normalize_text(payload.get("prompt"), max_length=_MAX_PROMPT_LENGTH)
    if not prompt:
        raise ValueError("Prompt-workbench Danbooru upsample requires prompt text.")
    return {
        "prompt": prompt,
        "negative_prompt_tags": _normalize_text(
            payload.get("negative_prompt_tags"),
            max_length=_MAX_OPTIONAL_TEXT_LENGTH,
        ),
        "ban_tags": _normalize_text(payload.get("ban_tags"), max_length=_MAX_OPTIONAL_TEXT_LENGTH),
    }


def _resolve_host_node_class_mappings() -> dict[str, Any]:
    try:
        import nodes as comfy_nodes  # type: ignore
    except Exception:
        return {}
    mappings = getattr(comfy_nodes, "NODE_CLASS_MAPPINGS", {})
    return mappings if isinstance(mappings, dict) else {}


def _resolve_host_node_entry() -> tuple[str, Any] | tuple[None, None]:
    mappings = _resolve_host_node_class_mappings()
    for alias in PROMPT_WORKBENCH_DANBOORU_NODE_ALIASES:
        node_class = mappings.get(alias)
        if node_class is not None:
            return alias, node_class
    return None, None


def build_prompt_workbench_danbooru_host_action_payload() -> dict[str, Any]:
    payload = build_default_prompt_workbench_host_actions()[PROMPT_WORKBENCH_DANBOORU_ACTION_ID]
    resolved_alias, node_class = _resolve_host_node_entry()
    if resolved_alias and node_class is not None:
        payload["available"] = True
        payload["resolved_node_alias"] = resolved_alias
        payload["availability"] = {
            "status": "ready",
            "detail": f"Host-installed Danbooru upsampler node '{resolved_alias}' is ready.",
        }
    else:
        payload["resolved_node_alias"] = ""
    return payload


def _extract_input_default(input_types: dict[str, Any], key: str, fallback: object) -> object:
    for section_name in ("required", "optional"):
        section = input_types.get(section_name)
        if not isinstance(section, dict) or key not in section:
            continue
        spec = section.get(key)
        if isinstance(spec, tuple) and len(spec) >= 2 and isinstance(spec[1], dict) and "default" in spec[1]:
            return spec[1]["default"]
    return fallback


def _resolve_node_defaults(node_class: Any) -> dict[str, Any]:
    try:
        input_types = node_class.INPUT_TYPES() if hasattr(node_class, "INPUT_TYPES") else {}
    except Exception:
        input_types = {}
    if not isinstance(input_types, dict):
        input_types = {}
    return {
        key: _extract_input_default(input_types, key, fallback)
        for key, fallback in _DEFAULT_NODE_INPUTS.items()
    }


def _resolve_callable_method(node_class: Any) -> tuple[Any, Any]:
    try:
        node_instance = node_class()
    except Exception as exc:  # pragma: no cover - defensive host edge case
        raise PromptWorkbenchDanbooruExecutionError(
            f"Danbooru upsampler host node could not be instantiated: {exc}"
        ) from exc
    function_name = str(getattr(node_class, "FUNCTION", getattr(node_instance, "FUNCTION", "upsample"))).strip() or "upsample"
    method = getattr(node_instance, function_name, None)
    if not callable(method):
        raise PromptWorkbenchDanbooruHostUnavailableError(
            "Danbooru upsampler host node did not expose a callable execution method."
        )
    return node_instance, method


def _build_method_kwargs(node_class: Any, normalized_request: dict[str, str]) -> dict[str, Any]:
    defaults = _resolve_node_defaults(node_class)
    return {
        "prompt": normalized_request["prompt"],
        "model_name": defaults["model_name"],
        "tag_length": defaults["tag_length"],
        "seed": defaults["seed"],
        "temperature": defaults["temperature"],
        "top_k": defaults["top_k"],
        "top_p": defaults["top_p"],
        "num_beams": defaults["num_beams"],
        "model_device": defaults["model_device"],
        "model_backend": defaults["model_backend"],
        "max_new_tokens": defaults["max_new_tokens"],
        "negative_prompt_tags": normalized_request["negative_prompt_tags"],
        "ban_tags": normalized_request["ban_tags"],
        "cfg_scale": defaults["cfg_scale"],
        "debug_logging": defaults["debug_logging"],
    }


def _invoke_host_method(method: Any, kwargs: dict[str, Any]) -> Any:
    signature = inspect.signature(method)
    accepts_var_keyword = any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in signature.parameters.values()
    )
    if accepts_var_keyword:
        return method(**kwargs)
    accepted_kwargs = {
        key: value
        for key, value in kwargs.items()
        if key in signature.parameters
    }
    return method(**accepted_kwargs)


def _extract_final_prompt(raw_result: Any) -> str:
    if isinstance(raw_result, tuple) and raw_result:
        return _normalize_text(raw_result[0], max_length=_MAX_PROMPT_LENGTH)
    if isinstance(raw_result, list) and raw_result:
        return _normalize_text(raw_result[0], max_length=_MAX_PROMPT_LENGTH)
    if isinstance(raw_result, str):
        return _normalize_text(raw_result, max_length=_MAX_PROMPT_LENGTH)
    return ""


def _derive_generated_suffix(prompt: str, final_prompt: str) -> str:
    normalized_prompt = prompt.strip()
    normalized_final = final_prompt.strip()
    prefix = f"{normalized_prompt}, "
    if normalized_prompt and normalized_final.startswith(prefix):
        return normalized_final[len(prefix) :].strip()
    if normalized_prompt == normalized_final:
        return ""
    return normalized_final


def execute_prompt_workbench_danbooru_request(payload: object) -> PromptWorkbenchDanbooruExecutionResult:
    normalized_request = _normalize_request_payload(payload)
    action_payload = build_prompt_workbench_danbooru_host_action_payload()
    if not bool(action_payload.get("available")):
        raise PromptWorkbenchDanbooruHostUnavailableError(
            str(action_payload.get("availability", {}).get("detail", "")).strip()
            or "Danbooru upsampler host node is unavailable."
        )

    resolved_alias, node_class = _resolve_host_node_entry()
    if not resolved_alias or node_class is None:
        raise PromptWorkbenchDanbooruHostUnavailableError(
            "Danbooru upsampler host node disappeared before execution."
        )

    _node_instance, method = _resolve_callable_method(node_class)
    method_kwargs = _build_method_kwargs(node_class, normalized_request)
    try:
        raw_result = _invoke_host_method(method, method_kwargs)
    except PromptWorkbenchDanbooruHostUnavailableError:
        raise
    except Exception as exc:
        raise PromptWorkbenchDanbooruExecutionError(
            f"Danbooru upsampler host execution failed: {exc}"
        ) from exc

    final_prompt = _extract_final_prompt(raw_result)
    if not final_prompt:
        raise PromptWorkbenchDanbooruExecutionError(
            "Danbooru upsampler host returned empty prompt text."
        )

    return PromptWorkbenchDanbooruExecutionResult(
        action_id=PROMPT_WORKBENCH_DANBOORU_ACTION_ID,
        final_prompt=final_prompt,
        generated_suffix=_derive_generated_suffix(normalized_request["prompt"], final_prompt),
        host_node_alias=resolved_alias,
        availability=action_payload["availability"],
        warnings=[],
        warning_codes=[],
    )


async def execute_prompt_workbench_danbooru_request_async(payload: object) -> dict[str, Any]:
    result = await asyncio.to_thread(execute_prompt_workbench_danbooru_request, payload)
    return result.to_payload()
