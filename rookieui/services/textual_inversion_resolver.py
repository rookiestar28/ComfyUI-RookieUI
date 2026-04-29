from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import os
import re
from typing import Any, Iterable

_EMBEDDING_EXTENSIONS = (".safetensors", ".pt", ".bin")
_EXPLICIT_EMBEDDING_RE = re.compile(
    r"(?<![\w./\\!$-])embedding:(?P<name>[\w.\-!$/\\]+)(?![\w./\\!$-])",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class TextualInversionEmbeddingInfo:
    name: str
    vectors: int = 1
    channels: tuple[str, ...] = ()


@dataclass(frozen=True)
class TextualInversionReference:
    token: str
    canonical_token: str
    name: str
    exists: bool
    syntax: str
    vectors: int = 1

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TextualInversionFix:
    offset: int
    name: str
    token: str
    vectors: int = 1

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TextualInversionResolveResult:
    resolved_text: str
    references: tuple[TextualInversionReference, ...] = ()
    missing_tokens: tuple[str, ...] = ()
    channel_mismatch_tokens: tuple[str, ...] = ()
    fixes: tuple[TextualInversionFix, ...] = ()

    def metadata(self) -> dict[str, Any]:
        metadata: dict[str, Any] = {}
        embeddings = [reference.canonical_token for reference in self.references if reference.exists]
        if embeddings:
            metadata["rookieui_textual_inversion_embeddings"] = embeddings
        if self.missing_tokens:
            metadata["rookieui_textual_inversion_missing"] = list(self.missing_tokens)
        if self.channel_mismatch_tokens:
            metadata["rookieui_textual_inversion_channel_mismatch"] = list(self.channel_mismatch_tokens)
        if self.fixes:
            metadata["rookieui_textual_inversion_fixes"] = [fix.to_payload() for fix in self.fixes]
        return metadata


def _normalize_embedding_name(name: str) -> str:
    normalized = str(name or "").strip()
    if normalized.lower().startswith("embedding:"):
        normalized = normalized[len("embedding:") :]
    normalized = normalized.replace("\\", "/").strip("/")
    return normalized


def _strip_embedding_extension(name: str) -> str:
    root, extension = os.path.splitext(name)
    if extension.lower() in _EMBEDDING_EXTENSIONS:
        return root
    return name


def _embedding_lookup_key(name: str) -> str:
    return _normalize_embedding_name(name).lower()


def _normalize_channel_name(channel: str | None) -> str:
    normalized = str(channel or "").strip().lower()
    if normalized in {"g", "global"}:
        return "clip_g"
    if normalized in {"l", "local"}:
        return "clip_l"
    return normalized


def _iter_aliases(name: str) -> set[str]:
    canonical = _normalize_embedding_name(name)
    if not canonical:
        return set()
    no_ext = _strip_embedding_extension(canonical)
    basename = canonical.rsplit("/", 1)[-1]
    basename_no_ext = _strip_embedding_extension(basename)
    aliases = {
        canonical,
        canonical.replace("/", "\\"),
        no_ext,
        no_ext.replace("/", "\\"),
        basename,
        basename_no_ext,
    }
    return {alias for alias in aliases if alias}


def _iter_inventory_entries(embedding_names: str | Iterable[str] | None) -> Iterable[str]:
    if embedding_names is None:
        return ()
    if isinstance(embedding_names, str):
        return [entry.strip() for entry in re.split(r"[\n,]+", embedding_names) if entry.strip()]
    return [str(entry).strip() for entry in embedding_names if str(entry).strip()]


def _parse_embedding_info(entry: str) -> TextualInversionEmbeddingInfo | None:
    parts = [part.strip() for part in str(entry or "").split("::") if part.strip()]
    if not parts:
        return None
    name = _normalize_embedding_name(parts[0])
    if not name:
        return None
    vectors = 1
    channels: tuple[str, ...] = ()
    for option in parts[1:]:
        key, separator, value = option.partition("=")
        if not separator:
            continue
        normalized_key = key.strip().lower()
        if normalized_key == "vectors":
            try:
                vectors = max(1, int(value.strip()))
            except (TypeError, ValueError):
                vectors = 1
        elif normalized_key == "channels":
            channels = tuple(
                _normalize_channel_name(channel)
                for channel in value.split("|")
                if _normalize_channel_name(channel)
            )
    return TextualInversionEmbeddingInfo(name=name, vectors=vectors, channels=channels)


def scan_textual_inversion_embeddings(embedding_directory: str | os.PathLike[str] | None) -> list[str]:
    if not embedding_directory:
        return []
    root = Path(embedding_directory)
    try:
        root = root.expanduser().resolve()
    except (OSError, RuntimeError):
        return []
    if not root.is_dir():
        return []

    names: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in _EMBEDDING_EXTENSIONS:
            continue
        try:
            relative = path.resolve().relative_to(root).as_posix()
        except (OSError, ValueError):
            continue
        names.append(relative)
    return names


def _build_embedding_lookup(
    *,
    embedding_names: str | Iterable[str] | None = None,
    embedding_directory: str | os.PathLike[str] | None = None,
) -> tuple[dict[str, TextualInversionEmbeddingInfo], re.Pattern[str] | None]:
    lookup: dict[str, TextualInversionEmbeddingInfo] = {}
    alias_values: set[str] = set()
    inventory_entries = [
        *_iter_inventory_entries(embedding_names),
        *scan_textual_inversion_embeddings(embedding_directory),
    ]
    for entry in inventory_entries:
        info = _parse_embedding_info(entry)
        if info is None:
            continue
        for alias in _iter_aliases(info.name):
            lookup.setdefault(_embedding_lookup_key(alias), info)
            alias_values.add(alias)

    if not alias_values:
        return lookup, None
    joined_aliases = "|".join(
        re.escape(alias)
        for alias in sorted(alias_values, key=lambda value: len(_embedding_lookup_key(value)), reverse=True)
    )
    pattern = re.compile(
        rf"(?<!embedding:)(?<![\w./\\!$-])(?P<name>{joined_aliases})(?![\w./\\!$-])",
        re.IGNORECASE,
    )
    return lookup, pattern


def _find_info(lookup: dict[str, TextualInversionEmbeddingInfo], name: str) -> TextualInversionEmbeddingInfo | None:
    return lookup.get(_embedding_lookup_key(name))


def _channel_matches(info: TextualInversionEmbeddingInfo, channel: str | None) -> bool:
    requested_channel = _normalize_channel_name(channel)
    if not requested_channel or not info.channels:
        return True
    return requested_channel in {_normalize_channel_name(value) for value in info.channels}


def _build_fixes(
    resolved_text: str,
    references: list[TextualInversionReference],
) -> tuple[TextualInversionFix, ...]:
    info_by_token = {
        reference.canonical_token: reference
        for reference in references
        if reference.exists
    }
    fixes: list[TextualInversionFix] = []
    for offset, token in enumerate(resolved_text.split()):
        clean_token = token.strip(" ,.;")
        reference = info_by_token.get(clean_token)
        if reference is None:
            continue
        fixes.append(
            TextualInversionFix(
                offset=offset,
                name=reference.name,
                token=reference.canonical_token,
                vectors=reference.vectors,
            )
        )
    return tuple(fixes)


def resolve_textual_inversion_prompt(
    prompt_text: str,
    *,
    embedding_names: str | Iterable[str] | None = None,
    embedding_directory: str | os.PathLike[str] | None = None,
    channel: str | None = None,
) -> TextualInversionResolveResult:
    lookup, bare_pattern = _build_embedding_lookup(
        embedding_names=embedding_names,
        embedding_directory=embedding_directory,
    )
    if not lookup:
        return TextualInversionResolveResult(resolved_text=str(prompt_text or ""))

    references: list[TextualInversionReference] = []
    missing_tokens: list[str] = []
    channel_mismatch_tokens: list[str] = []

    def replace_explicit(match: re.Match[str]) -> str:
        token = match.group(0)
        name = match.group("name")
        info = _find_info(lookup, name)
        if info is None or not _channel_matches(info, channel):
            fallback_name = _normalize_embedding_name(name)
            if info is None:
                missing_tokens.append(token)
            else:
                channel_mismatch_tokens.append(token)
            references.append(
                TextualInversionReference(
                    token=token,
                    canonical_token=fallback_name,
                    name=fallback_name,
                    exists=False,
                    syntax="explicit",
                )
            )
            return fallback_name
        canonical_token = f"embedding:{info.name}"
        references.append(
            TextualInversionReference(
                token=token,
                canonical_token=canonical_token,
                name=info.name,
                exists=True,
                syntax="explicit",
                vectors=info.vectors,
            )
        )
        return canonical_token

    resolved_text = _EXPLICIT_EMBEDDING_RE.sub(replace_explicit, str(prompt_text or ""))

    if bare_pattern is not None:
        def replace_bare(match: re.Match[str]) -> str:
            token = match.group("name")
            info = _find_info(lookup, token)
            if info is None:
                return token
            if not _channel_matches(info, channel):
                channel_mismatch_tokens.append(token)
                references.append(
                    TextualInversionReference(
                        token=token,
                        canonical_token=_normalize_embedding_name(token),
                        name=info.name,
                        exists=False,
                        syntax="bare",
                        vectors=info.vectors,
                    )
                )
                return token
            canonical_token = f"embedding:{info.name}"
            references.append(
                TextualInversionReference(
                    token=token,
                    canonical_token=canonical_token,
                    name=info.name,
                    exists=True,
                    syntax="bare",
                    vectors=info.vectors,
                )
            )
            return canonical_token

        resolved_text = bare_pattern.sub(replace_bare, resolved_text)

    resolved_text = " ".join(resolved_text.split())
    return TextualInversionResolveResult(
        resolved_text=resolved_text,
        references=tuple(references),
        missing_tokens=tuple(missing_tokens),
        channel_mismatch_tokens=tuple(channel_mismatch_tokens),
        fixes=_build_fixes(resolved_text, references),
    )
