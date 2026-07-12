from __future__ import annotations

from dataclasses import dataclass

from rookieui.contracts.family_template_manifest import FamilyTemplateManifestEntry
from rookieui.services.parity_matrix import normalize_scheduler_name

IGNORED_NEGATIVE_PROMPT = "IGNORED_NEGATIVE_PROMPT"
IGNORED_GENERIC_SCHEDULER = "IGNORED_GENERIC_SCHEDULER"


@dataclass(frozen=True)
class EffectiveParameterResolution:
    value: str
    warnings: tuple[str, ...] = ()
    warning_codes: tuple[str, ...] = ()


def resolve_effective_negative_prompt(
    profile_entry: FamilyTemplateManifestEntry,
    negative_prompt: str,
) -> EffectiveParameterResolution:
    mode = profile_entry.negative_prompt_mode
    if mode == "encoded":
        return EffectiveParameterResolution(value=negative_prompt)
    if mode not in {"zeroed", "unused"}:
        raise ValueError(f"Unsupported negative-prompt mode for profile '{profile_entry.id}'.")
    if not negative_prompt:
        return EffectiveParameterResolution(value="")
    # CRITICAL: never retain ignored prompt text in normalized output or PNG metadata.
    return EffectiveParameterResolution(
        value="",
        warnings=(
            f"Profile '{profile_entry.id}' does not encode a user negative prompt; the supplied value was ignored.",
        ),
        warning_codes=(IGNORED_NEGATIVE_PROMPT,),
    )


def resolve_effective_scheduler(
    profile_entry: FamilyTemplateManifestEntry,
    *,
    sampler_name: str,
    scheduler_input: str,
    default_scheduler: str,
) -> EffectiveParameterResolution:
    mode = profile_entry.scheduler_control_mode
    if mode == "generic":
        return EffectiveParameterResolution(
            value=normalize_scheduler_name(
                sampler_name,
                scheduler_input or None,
                default_scheduler=default_scheduler,
            )
        )
    if mode not in {"flux2", "ideogram4"}:
        raise ValueError(f"Unsupported scheduler-control mode for profile '{profile_entry.id}'.")
    if not scheduler_input:
        return EffectiveParameterResolution(value=mode)
    # IMPORTANT: owned scheduler nodes have no generic scheduler-name socket; diagnose legacy/stale payloads.
    return EffectiveParameterResolution(
        value=mode,
        warnings=(
            f"Profile '{profile_entry.id}' uses its dedicated {mode} scheduler; generic scheduler '{scheduler_input}' was ignored.",
        ),
        warning_codes=(IGNORED_GENERIC_SCHEDULER,),
    )
