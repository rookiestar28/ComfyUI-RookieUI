from __future__ import annotations


def coerce_int(
    value: object,
    field_name: str,
    *,
    default: int | None = None,
    via_str: bool = False,
    required_if_empty: bool = False,
) -> int:
    if value in (None, ""):
        if default is None:
            if required_if_empty:
                raise ValueError(f"{field_name} is required.")
        else:
            return default
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be an integer.")
    try:
        candidate = str(value).strip() if via_str else value
        return int(candidate)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer.") from exc


def coerce_float(
    value: object,
    field_name: str,
    *,
    default: float | None = None,
    via_str: bool = False,
    precision: int | None = None,
    error_label: str = "a float",
    required_if_empty: bool = False,
) -> float:
    if value in (None, ""):
        if default is None:
            if required_if_empty:
                raise ValueError(f"{field_name} is required.")
        else:
            return default
    try:
        candidate = str(value).strip() if via_str else value
        coerced = float(candidate)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be {error_label}.") from exc
    if precision is not None:
        return round(coerced, precision)
    return coerced


def coerce_bool(
    value: object,
    field_name: str,
    *,
    default: bool | None = None,
    strict: bool = True,
    error_label: str = "a boolean",
) -> bool:
    if value in (None, ""):
        if default is not None:
            return default
        if value == "":
            return False
        if strict:
            raise ValueError(f"{field_name} must be {error_label}.")
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    if strict:
        raise ValueError(f"{field_name} must be {error_label}.")
    # IMPORTANT: routes rely on non-strict truthy fallback for legacy dry_run payload compatibility.
    return bool(value)
