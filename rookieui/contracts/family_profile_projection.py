from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import fields
from typing import Any

from rookieui.contracts.family_template_manifest import FamilyTemplateManifestEntry


FAMILY_PROFILE_PROJECTION_CONTRACT_VERSION = "family-profile-projection-20260807-v1"


def _to_projection_value(value: object) -> object:
    """Convert immutable manifest values to JSON-compatible projection values."""

    if isinstance(value, tuple):
        return [_to_projection_value(item) for item in value]
    if isinstance(value, list):
        return [_to_projection_value(item) for item in value]
    if isinstance(value, Mapping):
        return {
            str(key): _to_projection_value(item)
            for key, item in value.items()
        }
    return value


def build_family_profile_projection(entry: FamilyTemplateManifestEntry) -> dict[str, Any]:
    """Return every declared manifest field without maintaining a second field list.

    The manifest dataclass remains the canonical declaration.  Derivers use this
    projection for deterministic snapshots and cross-surface contract checks;
    nested tuples are copied to lists so callers cannot mutate manifest state.
    """

    return {
        field.name: _to_projection_value(getattr(entry, field.name))
        for field in fields(FamilyTemplateManifestEntry)
    }


def build_family_profile_projection_entries(
    entries: Iterable[FamilyTemplateManifestEntry],
) -> tuple[dict[str, Any], ...]:
    """Project entries while preserving their declaration order."""

    return tuple(build_family_profile_projection(entry) for entry in entries)


def validate_runtime_adapter_bindings(
    entries: Iterable[FamilyTemplateManifestEntry],
    *,
    adapter_by_profile: Mapping[str, str],
    txt2img_builders: Mapping[str, Callable[..., object]],
    edit_builders: Mapping[str, Callable[..., object]],
    deferred_profile_ids: Iterable[str] = (),
) -> tuple[str, ...]:
    """Return deterministic errors for the executable adapter boundary.

    Runtime adapter IDs are declarative manifest data, while builder maps are
    executable bindings.  Keeping validation here makes missing callables,
    extra deferred bindings, and cross-flow collisions fail closed at import
    time without importing the workflow-builder module back into the contract.
    """

    manifest_entries = tuple(entries)
    errors: list[str] = []
    deferred_ids = {str(profile_id).strip().lower() for profile_id in deferred_profile_ids}
    entry_by_id: dict[str, FamilyTemplateManifestEntry] = {}

    for entry in manifest_entries:
        profile_id = str(entry.id or "").strip().lower()
        if not profile_id:
            errors.append("manifest entry has an empty profile id")
            continue
        if profile_id in entry_by_id:
            errors.append(f"duplicate manifest profile id '{profile_id}'")
        entry_by_id[profile_id] = entry
        if profile_id in deferred_ids:
            errors.append(f"deferred profile '{profile_id}' appears in shipped entries")

    shipped_non_sd = {
        profile_id: entry
        for profile_id, entry in entry_by_id.items()
        if entry.support_tier != "parity"
    }
    expected_adapter_by_flow: dict[str, set[str]] = {"txt2img": set(), "edit": set()}
    expected_adapter_ids: set[str] = set()

    for profile_id, entry in shipped_non_sd.items():
        adapter_id = str(adapter_by_profile.get(profile_id, "") or "").strip()
        if not adapter_id:
            errors.append(f"{profile_id}: missing runtime adapter id")
            continue
        expected_adapter_ids.add(adapter_id)
        flow_kind = str(entry.flow_kind or "").strip().lower()
        if flow_kind not in expected_adapter_by_flow:
            errors.append(f"{profile_id}: unsupported flow kind '{entry.flow_kind}'")
            continue
        required_surface_flow = "img2img" if flow_kind == "edit" else flow_kind
        if required_surface_flow not in {
            str(flow).strip().lower() for flow in entry.available_surface_flows
        }:
            errors.append(
                f"{profile_id}: required surface flow '{required_surface_flow}' is absent from available surface flows"
            )
        expected_adapter_by_flow[flow_kind].add(adapter_id)
        builders = txt2img_builders if flow_kind == "txt2img" else edit_builders
        builder = builders.get(adapter_id)
        if not callable(builder):
            errors.append(f"{profile_id}: adapter '{adapter_id}' has no callable {flow_kind} builder")
        opposite_builders = edit_builders if flow_kind == "txt2img" else txt2img_builders
        if adapter_id in opposite_builders:
            errors.append(f"{profile_id}: adapter '{adapter_id}' is dispatchable in both flows")

    declared_adapter_profiles = {
        str(profile_id).strip().lower()
        for profile_id, adapter_id in adapter_by_profile.items()
        if str(adapter_id or "").strip()
    }
    expected_profile_ids = set(shipped_non_sd)
    for unexpected_profile_id in sorted(declared_adapter_profiles - expected_profile_ids):
        errors.append(f"adapter map exposes non-shipped profile '{unexpected_profile_id}'")
    for missing_profile_id in sorted(expected_profile_ids - declared_adapter_profiles):
        errors.append(f"adapter map omits shipped profile '{missing_profile_id}'")
    for deferred_profile_id in sorted(declared_adapter_profiles & deferred_ids):
        errors.append(f"adapter map exposes deferred profile '{deferred_profile_id}'")

    for flow_kind, builders in (("txt2img", txt2img_builders), ("edit", edit_builders)):
        expected = expected_adapter_by_flow[flow_kind]
        actual = set(builders)
        for extra_adapter_id in sorted(actual - expected):
            errors.append(f"{flow_kind} builder map exposes unbound adapter '{extra_adapter_id}'")
        for missing_adapter_id in sorted(expected - actual):
            errors.append(f"{flow_kind} builder map omits adapter '{missing_adapter_id}'")
        for adapter_id, builder in builders.items():
            if not callable(builder):
                errors.append(f"{flow_kind} builder '{adapter_id}' is not callable")

    return tuple(dict.fromkeys(errors))


def assert_runtime_adapter_bindings(
    entries: Iterable[FamilyTemplateManifestEntry],
    *,
    adapter_by_profile: Mapping[str, str],
    txt2img_builders: Mapping[str, Callable[..., object]],
    edit_builders: Mapping[str, Callable[..., object]],
    deferred_profile_ids: Iterable[str] = (),
) -> None:
    """Raise a concise import-time error when executable bindings drift."""

    errors = validate_runtime_adapter_bindings(
        entries,
        adapter_by_profile=adapter_by_profile,
        txt2img_builders=txt2img_builders,
        edit_builders=edit_builders,
        deferred_profile_ids=deferred_profile_ids,
    )
    if errors:
        raise ValueError("Invalid family profile runtime adapter bindings: " + "; ".join(errors))
