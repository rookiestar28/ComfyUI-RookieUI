from __future__ import annotations

import re

from rookieui.contracts.prompt_dsl import PromptLoraActivation, PromptPreprocessResult
from rookieui.security.request_guard import normalize_prompt_text, resolve_inventory_selector
from rookieui.services.coercion import coerce_float, coerce_int

_EXTRA_NETWORK_RE = re.compile(r"<(\w+):([^>]+)>")
_AND_RE = re.compile(r"\bAND\b")
_BREAK_RE = re.compile(r"\bBREAK\b")
_SCHEDULE_RE = re.compile(r"\[[^][]*:[^][]*:[^][]*\]")


class _ExtraNetworkParams:
    def __init__(self, items: list[str]) -> None:
        self.items = items
        self.positional: list[str] = []
        self.named: dict[str, str] = {}
        for item in items:
            parts = item.split("=", 1)
            if len(parts) == 2:
                self.named[parts[0].strip().lower()] = parts[1].strip()
            else:
                self.positional.append(item.strip())


def _coerce_float(value: str, field_name: str) -> float:
    return coerce_float(value, field_name, error_label="numeric")


def _coerce_int(value: str, field_name: str) -> int:
    return coerce_int(value, field_name)


def _detect_prompt_feature_warnings(prompt_text: str) -> list[str]:
    warnings: list[str] = []
    if _AND_RE.search(prompt_text):
        warnings.append("A1111 prompt composition via AND is detected but not yet translated beyond raw prompt text.")
    if _BREAK_RE.search(prompt_text):
        warnings.append("A1111 BREAK conditioning semantics are detected but not yet translated beyond raw prompt text.")
    if _SCHEDULE_RE.search(prompt_text):
        warnings.append("A1111 prompt scheduling syntax is detected but not yet translated beyond raw prompt text.")
    return warnings


def _build_inline_lora_activation(
    params: _ExtraNetworkParams,
    *,
    inventory_selectors: list[str] | None,
    strict_match: bool,
) -> PromptLoraActivation:
    if not params.positional or not params.positional[0]:
        raise ValueError("inline LoRA syntax requires a model name.")

    lora_name = resolve_inventory_selector(
        params.positional[0],
        "inline_lora_name",
        default_value="",
        inventory_selectors=inventory_selectors,
        strict_match=strict_match,
    )
    if not lora_name:
        raise ValueError("inline LoRA syntax requires a model name.")

    clip_strength = 1.0
    if len(params.positional) > 1 and params.positional[1]:
        clip_strength = _coerce_float(params.positional[1], "inline_lora_clip_strength")
    if "te" in params.named:
        clip_strength = _coerce_float(params.named["te"], "inline_lora_clip_strength")

    model_strength = clip_strength
    if len(params.positional) > 2 and params.positional[2]:
        model_strength = _coerce_float(params.positional[2], "inline_lora_model_strength")
    if "unet" in params.named:
        model_strength = _coerce_float(params.named["unet"], "inline_lora_model_strength")

    dyn_dim = None
    if len(params.positional) > 3 and params.positional[3]:
        dyn_dim = _coerce_int(params.positional[3], "inline_lora_dyn")
    if "dyn" in params.named:
        dyn_dim = _coerce_int(params.named["dyn"], "inline_lora_dyn")

    return PromptLoraActivation(
        name=lora_name,
        strength_model=round(model_strength, 3),
        strength_clip=round(clip_strength, 3),
        dyn_dim=dyn_dim,
        source="inline",
    )


def _extract_inline_activations(
    prompt_text: str,
    *,
    inventory_selectors: list[str] | None,
    strict_match: bool,
) -> tuple[str, list[PromptLoraActivation], list[str]]:
    activations: list[PromptLoraActivation] = []
    warnings: list[str] = []

    def _replace(match: re.Match[str]) -> str:
        network_name = match.group(1).strip().lower()
        params = _ExtraNetworkParams([item.strip() for item in match.group(2).split(":") if item.strip()])
        if network_name in {"lora", "lyco"}:
            activations.append(
                _build_inline_lora_activation(
                    params,
                    inventory_selectors=inventory_selectors,
                    strict_match=strict_match,
                )
            )
            return ""

        warnings.append(f"Unsupported A1111 extra network was removed from the prompt: <{network_name}:...>.")
        return ""

    cleaned = _EXTRA_NETWORK_RE.sub(_replace, prompt_text)
    cleaned = normalize_prompt_text(cleaned, "prompt", required=False)
    return cleaned, activations, warnings


def merge_lora_activations(
    inline_activations: list[PromptLoraActivation],
    *,
    explicit_lora_name: str,
    explicit_strength_model: float,
    explicit_strength_clip: float,
) -> list[PromptLoraActivation]:
    merged = list(inline_activations)
    if not explicit_lora_name:
        return merged

    explicit_activation = PromptLoraActivation(
        name=explicit_lora_name,
        strength_model=round(float(explicit_strength_model), 3),
        strength_clip=round(float(explicit_strength_clip), 3),
        source="selector",
    )
    # IMPORTANT: keep the selector merge deterministic; explicit UI LoRA must override the matching inline token instead of silently stacking the same host LoRA twice.
    for index, activation in enumerate(merged):
        if activation.name == explicit_activation.name:
            merged[index] = explicit_activation
            return merged

    merged.append(explicit_activation)
    return merged


def preprocess_prompt_bundle(
    prompt: str,
    negative_prompt: str,
    *,
    inventory_loras: list[str] | None = None,
    strict_match: bool = False,
) -> PromptPreprocessResult:
    cleaned_prompt, prompt_loras, prompt_warnings = _extract_inline_activations(
        prompt,
        inventory_selectors=inventory_loras,
        strict_match=strict_match,
    )
    cleaned_negative_prompt, negative_loras, negative_warnings = _extract_inline_activations(
        negative_prompt,
        inventory_selectors=inventory_loras,
        strict_match=strict_match,
    )

    warnings = [
        *_detect_prompt_feature_warnings(cleaned_prompt),
        *_detect_prompt_feature_warnings(cleaned_negative_prompt),
        *prompt_warnings,
        *negative_warnings,
    ]
    return PromptPreprocessResult(
        cleaned_prompt=cleaned_prompt,
        cleaned_negative_prompt=cleaned_negative_prompt,
        lora_activations=[*prompt_loras, *negative_loras],
        prompt_warnings=list(dict.fromkeys(warnings)),
    )
