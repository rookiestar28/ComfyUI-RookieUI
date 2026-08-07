"""Deterministic, offline architecture contract validation.

The checker treats source as data. It never imports project or reference code,
runs subprocesses, accesses the network, or writes repository files.
"""

from __future__ import annotations

import ast
import json
import os
import posixpath
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping


_SKIPPED_PARTS = {
    ".git",
    ".planning",
    ".tmp",
    ".venv",
    ".venv-wsl",
    "node_modules",
    "reference",
    "REFERENCE",
}
_SNAPSHOT_SUFFIXES = {".js", ".json", ".mjs", ".py", ".ps1", ".sh"}


@dataclass(frozen=True, order=True)
class ArchitectureViolation:
    code: str
    path: str
    detail: str


@dataclass(frozen=True)
class _JsToken:
    kind: str
    value: str


def normalize_repo_path(path: str | Path) -> str:
    return str(path).replace("\\", "/").lstrip("./")


def load_contract(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported architecture contract schema")
    return payload


def snapshot_repository(root: str | Path, contract: Mapping[str, Any]) -> dict[str, str]:
    root_path = Path(root).resolve()
    snapshot: dict[str, str] = {}
    for current_root, dir_names, file_names in os.walk(root_path, followlinks=False):
        dir_names[:] = [name for name in dir_names if name not in _SKIPPED_PARTS]
        current = Path(current_root)
        for file_name in file_names:
            path = current / file_name
            if path.suffix.lower() not in _SNAPSHOT_SUFFIXES:
                continue
            relative = path.relative_to(root_path)
            snapshot[normalize_repo_path(relative)] = path.read_text(encoding="utf-8")

    required = set(contract.get("required_guards", []))
    required.update(contract.get("budgets", {}).keys())
    required.add(contract["typed_coverage"]["config"])
    required.add(contract["test_discovery"]["package"])
    for path in required:
        normalized = normalize_repo_path(path)
        absolute = root_path / Path(normalized)
        if absolute.is_file() and normalized not in snapshot:
            snapshot[normalized] = absolute.read_text(encoding="utf-8")
    return snapshot


def _violation(code: str, path: str, detail: str) -> ArchitectureViolation:
    return ArchitectureViolation(code=code, path=normalize_repo_path(path), detail=detail)


def _resolve_esm_path(source_path: str, specifier: str) -> str | None:
    if not specifier.startswith("."):
        return None
    return normalize_repo_path(posixpath.normpath(posixpath.join(posixpath.dirname(source_path), specifier)))


def _tokenize_javascript(source: str) -> list[_JsToken]:
    tokens: list[_JsToken] = []
    index = 0
    length = len(source)
    while index < length:
        char = source[index]
        if char.isspace():
            index += 1
            continue
        if source.startswith("//", index):
            newline = source.find("\n", index + 2)
            index = length if newline < 0 else newline + 1
            continue
        if source.startswith("/*", index):
            end = source.find("*/", index + 2)
            index = length if end < 0 else end + 2
            continue
        if char in {'"', "'", "`"}:
            quote = char
            index += 1
            value: list[str] = []
            while index < length:
                char = source[index]
                if char == "\\" and index + 1 < length:
                    value.extend((char, source[index + 1]))
                    index += 2
                    continue
                if char == quote:
                    index += 1
                    break
                value.append(char)
                index += 1
            # Template text is deliberately opaque; import-like prose inside it is not a dependency declaration.
            if quote != "`":
                tokens.append(_JsToken("string", "".join(value)))
            continue
        if char.isalpha() or char in {"_", "$"}:
            end = index + 1
            while end < length and (source[end].isalnum() or source[end] in {"_", "$"}):
                end += 1
            tokens.append(_JsToken("identifier", source[index:end]))
            index = end
            continue
        tokens.append(_JsToken("punctuation", char))
        index += 1
    return tokens


def _collect_esm_specifiers(source: str) -> list[str]:
    tokens = _tokenize_javascript(source)
    specifiers: list[str] = []
    for index, token in enumerate(tokens):
        if token.kind != "identifier" or token.value not in {"import", "export"}:
            continue
        cursor = index + 1
        if token.value == "import" and cursor < len(tokens):
            next_token = tokens[cursor]
            if next_token.kind == "string":
                specifiers.append(next_token.value)
                continue
            if next_token.value == "(" and cursor + 1 < len(tokens) and tokens[cursor + 1].kind == "string":
                specifiers.append(tokens[cursor + 1].value)
                continue
        while cursor < len(tokens) and cursor - index <= 256:
            current = tokens[cursor]
            if current.value == ";":
                break
            if current.kind == "identifier" and current.value == "from":
                if cursor + 1 < len(tokens) and tokens[cursor + 1].kind == "string":
                    specifiers.append(tokens[cursor + 1].value)
                break
            cursor += 1
    return specifiers


def _python_module_name(path: str) -> str:
    module = path.removesuffix(".py").replace("/", ".")
    return module.removesuffix(".__init__")


def _resolve_python_import_from(own_module: str, node: ast.ImportFrom, *, is_package: bool) -> list[str]:
    if node.level == 0:
        return [node.module] if node.module else []
    package_parts = own_module.split(".") if is_package else own_module.split(".")[:-1]
    ascents = node.level - 1
    if ascents > len(package_parts):
        return []
    base_parts = package_parts[: len(package_parts) - ascents]
    if node.module:
        return [".".join([*base_parts, *node.module.split(".")])]
    return [".".join([*base_parts, alias.name]) for alias in node.names]


def _python_domain_imports(
    path: str,
    source: str,
    domain_root: str,
    allowed_edges: set[tuple[str, str]],
) -> list[ArchitectureViolation]:
    violations: list[ArchitectureViolation] = []
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as error:
        return [_violation("SOURCE_PARSE_ERROR", path, f"Python syntax error at line {error.lineno}")]
    own_module = _python_module_name(path)
    prefix = domain_root.replace("/", ".") + "."
    for node in ast.walk(tree):
        imported: list[str] = []
        if isinstance(node, ast.ImportFrom):
            imported.extend(_resolve_python_import_from(own_module, node, is_package=path.endswith("/__init__.py")))
        elif isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        for module in imported:
            if module.startswith(prefix) and module != own_module and (path, module) not in allowed_edges:
                violations.append(_violation("CROSS_DOMAIN_IMPORT", path, f"imports sibling domain {module}"))
    return violations


def _validate_dependency_directions(files: Mapping[str, str], contract: Mapping[str, Any]) -> list[ArchitectureViolation]:
    violations: list[ArchitectureViolation] = []
    backend_root = normalize_repo_path(contract["backend_domain_root"])
    allowed_backend_edges = {
        (normalize_repo_path(source), target)
        for source, target in contract.get("allowed_backend_domain_edges", [])
    }
    for path, source in files.items():
        if path.startswith(backend_root + "/") and path.endswith(".py"):
            violations.extend(_python_domain_imports(path, source, backend_root, allowed_backend_edges))

    frontend_domains = {normalize_repo_path(path) for path in contract["frontend_domain_files"]}
    facade = normalize_repo_path(contract["frontend_facade"])
    for path in sorted(frontend_domains):
        source = files.get(path, "")
        allowed_dependencies = {
            normalize_repo_path(item)
            for item in contract.get("allowed_frontend_dependencies", {}).get(path, [])
        }
        for specifier in _collect_esm_specifiers(source):
            target = _resolve_esm_path(path, specifier)
            if target == facade:
                violations.append(_violation("FACADE_BACK_IMPORT", path, f"imports compatibility facade {target}"))
            elif target in frontend_domains and target != path:
                violations.append(_violation("CROSS_DOMAIN_IMPORT", path, f"imports sibling domain {target}"))
            elif target and target not in allowed_dependencies:
                violations.append(
                    _violation("FORBIDDEN_DOMAIN_DEPENDENCY", path, f"imports unreviewed dependency {target}")
                )
    return violations


def _validate_composition_roots(files: Mapping[str, str], contract: Mapping[str, Any]) -> list[ArchitectureViolation]:
    violations: list[ArchitectureViolation] = []
    for path, rule in contract["composition_roots"].items():
        source = files.get(path)
        if source is None:
            violations.append(_violation("COMPOSITION_ROOT_MISSING", path, "composition root is absent"))
            continue
        try:
            tree = ast.parse(source, filename=path)
        except SyntaxError as error:
            violations.append(_violation("SOURCE_PARSE_ERROR", path, f"Python syntax error at line {error.lineno}"))
            continue
        allowed_functions = set(rule.get("allowed_functions", []))
        actual_functions = {
            node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        required_functions = set(rule.get("required_functions", []))
        missing_required = sorted(required_functions - actual_functions)
        if missing_required:
            violations.append(
                _violation(
                    "COMPOSITION_REQUIRED_FUNCTION_MISSING",
                    path,
                    f"missing required functions: {', '.join(missing_required)}",
                )
            )
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name not in allowed_functions:
                violations.append(
                    _violation("COMPOSITION_HANDLER_LOGIC", path, f"unexpected function {node.name}")
                )
    return violations


def _validate_family_truth(files: Mapping[str, str], contract: Mapping[str, Any]) -> list[ArchitectureViolation]:
    violations: list[ArchitectureViolation] = []
    rule = contract["family_truth"]
    canonical = normalize_repo_path(rule["canonical_owner"])
    assignment = rule["assignment_name"]
    for path, source in files.items():
        if not path.startswith("rookieui/") or not path.endswith(".py") or path == canonical:
            continue
        try:
            tree = ast.parse(source, filename=path)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            targets: list[ast.expr] = []
            if isinstance(node, ast.Assign):
                targets = list(node.targets)
            elif isinstance(node, ast.AnnAssign):
                targets = [node.target]
            if any(isinstance(target, ast.Name) and target.id == assignment for target in targets):
                violations.append(_violation("ALTERNATE_FAMILY_TRUTH", path, f"assigns canonical name {assignment}"))
    for path, markers in rule["projection_markers"].items():
        source = files.get(path, "")
        missing = [marker for marker in markers if marker not in source]
        if missing:
            violations.append(_violation("PROJECTION_CONTRACT_MISSING", path, f"missing markers: {', '.join(missing)}"))
    return violations


def _validate_disposal(files: Mapping[str, str], contract: Mapping[str, Any]) -> list[ArchitectureViolation]:
    violations: list[ArchitectureViolation] = []
    for path, markers in contract["disposal_contracts"].items():
        source = files.get(path, "")
        missing = [marker for marker in markers if marker not in source]
        if missing:
            violations.append(_violation("DISPOSAL_CONTRACT_MISSING", path, f"missing markers: {', '.join(missing)}"))
    return violations


def _collect_direct_esm_exports(source: str) -> tuple[set[str], list[str]]:
    tokens = _tokenize_javascript(source)
    exports: set[str] = set()
    star_specifiers: list[str] = []
    index = 0
    while index < len(tokens):
        if tokens[index] != _JsToken("identifier", "export"):
            index += 1
            continue
        cursor = index + 1
        if cursor < len(tokens) and tokens[cursor] == _JsToken("identifier", "async"):
            cursor += 1
        if cursor >= len(tokens):
            break
        current = tokens[cursor]
        if current.kind == "identifier" and current.value in {"function", "class", "const", "let", "var"}:
            if cursor + 1 < len(tokens) and tokens[cursor + 1].kind == "identifier":
                exports.add(tokens[cursor + 1].value)
        elif current.value == "{":
            cursor += 1
            item: list[_JsToken] = []
            while cursor < len(tokens) and tokens[cursor].value != "}":
                if tokens[cursor].value == ",":
                    identifiers = [token.value for token in item if token.kind == "identifier"]
                    if identifiers:
                        exports.add(identifiers[-1] if "as" in identifiers else identifiers[0])
                    item = []
                else:
                    item.append(tokens[cursor])
                cursor += 1
            identifiers = [token.value for token in item if token.kind == "identifier"]
            if identifiers:
                exports.add(identifiers[-1] if "as" in identifiers else identifiers[0])
        elif current.value == "*":
            while cursor < len(tokens) and cursor - index <= 16:
                if tokens[cursor] == _JsToken("identifier", "from"):
                    if cursor + 1 < len(tokens) and tokens[cursor + 1].kind == "string":
                        star_specifiers.append(tokens[cursor + 1].value)
                    break
                cursor += 1
        index += 1
    return exports, star_specifiers


def _collect_esm_exports(path: str, files: Mapping[str, str], seen: set[str] | None = None) -> set[str]:
    seen = set() if seen is None else seen
    if path in seen:
        return set()
    seen.add(path)
    source = files.get(path, "")
    exports, star_specifiers = _collect_direct_esm_exports(source)
    for specifier in star_specifiers:
        target = _resolve_esm_path(path, specifier)
        if target:
            exports.update(_collect_esm_exports(target, files, seen))
    return exports


def _validate_facade(files: Mapping[str, str], contract: Mapping[str, Any]) -> list[ArchitectureViolation]:
    facade = normalize_repo_path(contract["frontend_facade"])
    actual = _collect_esm_exports(facade, files)
    expected = set(contract["facade_exports"])
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        return [_violation("API_FACADE_EXPORT_DRIFT", facade, f"missing={missing}; extra={extra}")]
    return []


def _validate_typed_coverage(files: Mapping[str, str], contract: Mapping[str, Any]) -> list[ArchitectureViolation]:
    rule = contract["typed_coverage"]
    path = normalize_repo_path(rule["config"])
    try:
        config = json.loads(files[path])
    except (KeyError, json.JSONDecodeError):
        return [_violation("TYPED_COVERAGE_REDUCED", path, "missing or invalid TypeScript config")]
    options = config.get("compilerOptions", {})
    includes = {normalize_repo_path(item) for item in config.get("include", [])}
    js_count = sum(item.endswith(".js") for item in includes)
    required = {normalize_repo_path(item) for item in rule["required_files"]}
    if (
        options.get("checkJs") is not True
        or options.get("noEmit") is not True
        or js_count < int(rule["minimum_js_files"])
        or not required.issubset(includes)
        or config.get("exclude")
    ):
        return [_violation("TYPED_COVERAGE_REDUCED", path, f"js_count={js_count}; missing={sorted(required - includes)}")]
    return []


def _validate_governed_membership(files: Mapping[str, str], contract: Mapping[str, Any]) -> list[ArchitectureViolation]:
    violations: list[ArchitectureViolation] = []
    for rule in contract["governed_roots"]:
        root = normalize_repo_path(rule["root"])
        extension = rule["extension"]
        allowed = {normalize_repo_path(path) for path in rule["allowed_files"]}
        actual = {path for path in files if path.startswith(root + "/") and path.endswith(extension)}
        for path in sorted(actual - allowed):
            violations.append(_violation("UNLISTED_GOVERNED_FILE", path, f"not listed under governed root {root}"))
        for path in sorted(allowed - actual):
            violations.append(_violation("GOVERNED_FILE_MISSING", path, f"listed under governed root {root}"))
    return violations


def _validate_budgets(files: Mapping[str, str], contract: Mapping[str, Any]) -> list[ArchitectureViolation]:
    violations: list[ArchitectureViolation] = []
    for path, budget in contract["budgets"].items():
        source = files.get(path)
        if source is None:
            violations.append(_violation("BUDGETED_FILE_MISSING", path, "budgeted ownership surface is absent"))
            continue
        byte_count = len(source.encode("utf-8"))
        lines = source.splitlines()
        line_count = len(lines)
        max_line_length = max((len(line) for line in lines), default=0)
        if byte_count > budget["max_bytes"] or line_count > budget["max_lines"]:
            violations.append(
                _violation("OWNERSHIP_BUDGET_EXCEEDED", path, f"bytes={byte_count}; lines={line_count}")
            )
        if (
            byte_count < budget["min_bytes"]
            or line_count < budget["min_lines"]
            or max_line_length > budget["max_line_length"]
        ):
            violations.append(
                _violation(
                    "SOURCE_PACKING_DETECTED",
                    path,
                    f"bytes={byte_count}; lines={line_count}; max_line={max_line_length}",
                )
            )
    return violations


def _validate_guards_and_discovery(files: Mapping[str, str], contract: Mapping[str, Any]) -> list[ArchitectureViolation]:
    violations: list[ArchitectureViolation] = []
    for path in contract["required_guards"]:
        if normalize_repo_path(path) not in files:
            violations.append(_violation("REQUIRED_GUARD_MISSING", path, "required existing guard is absent"))
    rule = contract["test_discovery"]
    package_path = normalize_repo_path(rule["package"])
    try:
        package = json.loads(files[package_path])
    except (KeyError, json.JSONDecodeError):
        return violations + [_violation("TEST_DISCOVERY_WEAKENED", package_path, "missing or invalid package manifest")]
    unit_script = package.get("scripts", {}).get("test:unit")
    corpus = "\n".join(files.get(path, "") for path in (package_path, "vitest.config.js", "vitest.config.mjs"))
    if unit_script != rule["unit_script"] or any(token in corpus for token in rule["forbidden_tokens"]):
        violations.append(_violation("TEST_DISCOVERY_WEAKENED", package_path, f"test:unit={unit_script!r}"))
    return violations


def _validate_enforcement_artifacts(
    files: Mapping[str, str], contract: Mapping[str, Any]
) -> list[ArchitectureViolation]:
    return [
        _violation("ENFORCEMENT_ARTIFACT_MISSING", path, "required conformance artifact is absent")
        for path in contract.get("required_enforcement_artifacts", [])
        if normalize_repo_path(path) not in files
    ]


def validate_snapshot(files: Mapping[str, str], contract: Mapping[str, Any]) -> list[ArchitectureViolation]:
    normalized_files = {normalize_repo_path(path): source for path, source in files.items()}
    violations: list[ArchitectureViolation] = []
    violations.extend(_validate_governed_membership(normalized_files, contract))
    violations.extend(_validate_dependency_directions(normalized_files, contract))
    violations.extend(_validate_composition_roots(normalized_files, contract))
    violations.extend(_validate_family_truth(normalized_files, contract))
    violations.extend(_validate_disposal(normalized_files, contract))
    violations.extend(_validate_facade(normalized_files, contract))
    violations.extend(_validate_typed_coverage(normalized_files, contract))
    violations.extend(_validate_budgets(normalized_files, contract))
    violations.extend(_validate_guards_and_discovery(normalized_files, contract))
    violations.extend(_validate_enforcement_artifacts(normalized_files, contract))
    return sorted(set(violations))


def validate_repository(root: str | Path, contract_path: str | Path) -> list[ArchitectureViolation]:
    contract = load_contract(contract_path)
    return validate_snapshot(snapshot_repository(root, contract), contract)
