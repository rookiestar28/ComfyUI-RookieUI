from __future__ import annotations

from dataclasses import asdict, dataclass
import os
import re
from typing import Any, Iterable

_EMBEDDING_EXTENSIONS = (".safetensors", ".pt", ".bin")
_MAX_EMBEDDING_DIRECTORY_LENGTH = 4096
_EMBEDDING_DIRECTORY_REJECTION = (
    "embedding_directory must be empty or name a ComfyUI-registered embeddings folder "
    "(or a subfolder of one); other filesystem paths are not scanned."
)
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


def _load_folder_paths_module() -> Any | None:
    try:
        import folder_paths
    except Exception:
        return None
    return folder_paths


def _lexical_absolute_path(value: str) -> str:
    # abspath/normpath/normcase are pure string operations here; they never stat the path.
    return os.path.normcase(os.path.normpath(os.path.abspath(value)))


def _name_case_key(name: str) -> str:
    # normcase folds case on Windows but also turns "/" into "\\"; keep "/" as the separator.
    return os.path.normcase(name).replace("\\", "/")


def _registered_embedding_roots(folder_paths_module: Any) -> tuple[str, ...]:
    get_folder_paths = getattr(folder_paths_module, "get_folder_paths", None)
    if not callable(get_folder_paths):
        return ()
    try:
        roots = get_folder_paths("embeddings")
    except Exception:
        return ()
    if not isinstance(roots, (list, tuple)):
        return ()
    return tuple(
        dict.fromkeys(_lexical_absolute_path(root) for root in roots if isinstance(root, str) and root.strip())
    )


def _relative_to_registered_root(candidate: str, roots: tuple[str, ...]) -> str | None:
    for root in roots:
        try:
            if os.path.commonpath((root, candidate)) != root:
                continue
        except ValueError:
            # Different drives or mixed absolute/relative forms are never inside the root.
            continue
        relative = os.path.relpath(candidate, root)
        return "" if relative == os.curdir else relative.replace(os.sep, "/").strip("/")
    return None


def list_registered_embedding_inventory(embedding_directory: str | os.PathLike[str] | None) -> list[str]:
    """Return root-relative embedding names for a ComfyUI-registered embeddings folder.

    The value only selects a host-registered root (or a subfolder of one); the names come from
    the host's own embeddings inventory, never from walking the client-supplied path.
    """
    if embedding_directory is None:
        return []
    if isinstance(embedding_directory, os.PathLike):
        embedding_directory = os.fspath(embedding_directory)
    if not isinstance(embedding_directory, str):
        raise ValueError(_EMBEDDING_DIRECTORY_REJECTION)
    requested = embedding_directory.strip()
    if not requested:
        return []
    # CRITICAL: embedding_directory is attacker-controlled through /prompt. Decide containment
    # lexically against host-registered roots *before* any filesystem call, and never walk,
    # resolve or stat the requested path; Path(value).resolve().rglob() here was the Registry
    # arbitrary-file-read finding (directory listing / existence oracle via prompt metadata).
    if len(requested) > _MAX_EMBEDDING_DIRECTORY_LENGTH or any(
        ord(character) < 32 or ord(character) == 127 for character in requested
    ):
        raise ValueError(_EMBEDDING_DIRECTORY_REJECTION)
    folder_paths_module = _load_folder_paths_module()
    if folder_paths_module is None:
        raise ValueError(_EMBEDDING_DIRECTORY_REJECTION)
    subfolder = _relative_to_registered_root(
        _lexical_absolute_path(requested),
        _registered_embedding_roots(folder_paths_module),
    )
    if subfolder is None:
        raise ValueError(_EMBEDDING_DIRECTORY_REJECTION)

    get_filename_list = getattr(folder_paths_module, "get_filename_list", None)
    if not callable(get_filename_list):
        raise ValueError(_EMBEDDING_DIRECTORY_REJECTION)
    try:
        inventory = get_filename_list("embeddings")
    except Exception as exc:
        raise ValueError(_EMBEDDING_DIRECTORY_REJECTION) from exc

    subfolder_key = _name_case_key(subfolder)
    names: list[str] = []
    for entry in inventory if isinstance(inventory, (list, tuple)) else ():
        if not isinstance(entry, str):
            continue
        name = entry.replace("\\", "/").strip("/")
        if not name or os.path.splitext(name)[1].lower() not in _EMBEDDING_EXTENSIONS:
            continue
        if subfolder_key and not _name_case_key(name).startswith(subfolder_key + "/"):
            continue
        names.append(name)
    return sorted(dict.fromkeys(names))


def _build_embedding_lookup(
    *,
    embedding_names: str | Iterable[str] | None = None,
    embedding_directory: str | os.PathLike[str] | None = None,
) -> tuple[dict[str, TextualInversionEmbeddingInfo], re.Pattern[str] | None]:
    lookup: dict[str, TextualInversionEmbeddingInfo] = {}
    alias_values: set[str] = set()
    inventory_entries = [
        *_iter_inventory_entries(embedding_names),
        *list_registered_embedding_inventory(embedding_directory),
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
