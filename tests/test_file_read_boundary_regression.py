from __future__ import annotations

import contextlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from rookieui import nodes
from rookieui.api import route_spec
from rookieui.security.route_guard import SafeRouteRegistrar
from rookieui.services import asset_store
from rookieui.services import prompt_workbench_state as state
from rookieui.services import prompt_workbench_translation as translation
from rookieui.services import textual_inversion_resolver as resolver

_FIXTURE_ROOT = Path(__file__).resolve().parents[1] / ".tmp" / "file-read-boundary-fixtures"
_REJECTION_FRAGMENT = "ComfyUI-registered embeddings folder"
_OUTSIDE_VALUE = "SYNTHETIC-OUTSIDE-VALUE"


def _fixture_dir(test: unittest.TestCase) -> Path:
    _FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    holder = tempfile.TemporaryDirectory(dir=_FIXTURE_ROOT)
    test.addCleanup(holder.cleanup)
    return Path(holder.name).resolve()


@contextlib.contextmanager
def _deny_filesystem_probes():
    """Fail the test if code under test enumerates or stats the filesystem."""

    def deny(*_args, **_kwargs):
        raise AssertionError("filesystem probe on a client-controlled path")

    patches = [
        mock.patch("os.stat", side_effect=deny),
        mock.patch("os.lstat", side_effect=deny),
        mock.patch("os.scandir", side_effect=deny),
        mock.patch("os.listdir", side_effect=deny),
        mock.patch("os.walk", side_effect=deny),
        mock.patch("os.path.exists", side_effect=deny),
        mock.patch("os.path.isdir", side_effect=deny),
        mock.patch("os.path.isfile", side_effect=deny),
        mock.patch("os.path.realpath", side_effect=deny),
    ]
    for name in ("rglob", "glob", "iterdir", "resolve", "exists", "is_dir", "is_file", "stat"):
        patches.append(mock.patch.object(Path, name, deny))
    with contextlib.ExitStack() as stack:
        for patcher in patches:
            stack.enter_context(patcher)
        yield


class _FakeFolderPaths:
    def __init__(self, roots: list[str], names: list[str]) -> None:
        self.roots = roots
        self.names = names
        self.calls: list[tuple[str, str]] = []

    def get_folder_paths(self, folder_name: str) -> list[str]:
        self.calls.append(("get_folder_paths", folder_name))
        return list(self.roots)

    def get_filename_list(self, folder_name: str) -> list[str]:
        self.calls.append(("get_filename_list", folder_name))
        return list(self.names)


class _FakeClip:
    def tokenize(self, text, return_word_ids=False):
        if return_word_ids:
            return {"l": [[("BOS", 1.0, 0), (text, 1.0, 1), ("EOS", 1.0, 0)]]}
        return {"l": [[("BOS", 1.0), (text, 1.0), ("EOS", 1.0)]]}

    def encode_from_tokens_scheduled(self, tokens, add_dict=None):
        metadata = {"pooled_output": "pooled"}
        metadata.update(add_dict or {})
        return [[f"cond::{tokens['l'][0][1][0]}", metadata]]


class EmbeddingDirectoryBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        base = _fixture_dir(self)
        self.registered = base / "models" / "embeddings"
        (self.registered / "style").mkdir(parents=True)
        (self.registered / "style" / "registered_style.pt").write_bytes(b"synthetic")
        self.outside = base / "private"
        self.outside.mkdir()
        (self.outside / "secret_probe.pt").write_bytes(b"synthetic")
        self.folder_paths = _FakeFolderPaths(
            [str(self.registered)],
            [
                os.path.join("style", "registered_style.pt"),
                "root_style.safetensors",
                "notes.txt",
                "legacy_model.ckpt",
            ],
        )
        modules = mock.patch.dict(sys.modules, {"folder_paths": self.folder_paths})
        modules.start()
        self.addCleanup(modules.stop)

    def _assert_rejected(self, value: object) -> str:
        with _deny_filesystem_probes():
            with self.assertRaises(ValueError) as caught:
                resolver.resolve_textual_inversion_prompt(
                    "portrait secret_probe registered_style",
                    embedding_directory=value,  # type: ignore[arg-type]
                )
        message = str(caught.exception)
        self.assertIn(_REJECTION_FRAGMENT, message)
        self.assertNotIn(str(self.outside), message)
        self.assertNotIn(str(self.registered), message)
        return message

    def test_node_rejects_unregistered_directory_instead_of_leaking_names(self) -> None:
        node = nodes.RookieUIA1111CLIPTextEncode()
        try:
            conditioning, = node.encode(
                _FakeClip(),
                "portrait secret_probe",
                embedding_directory=str(self.outside),
            )
        except ValueError as exc:
            self.assertIn(_REJECTION_FRAGMENT, str(exc))
        else:
            self.fail(
                "unregistered embedding_directory was scanned; leaked metadata: "
                f"{conditioning[0][1].get('rookieui_textual_inversion_embeddings')}"
            )

    def test_sdxl_node_rejects_unregistered_directory(self) -> None:
        node = nodes.RookieUIA1111CLIPTextEncodeSDXL()
        with self.assertRaises(ValueError):
            node.encode(
                mock.Mock(),
                1024,
                1024,
                0,
                0,
                1024,
                1024,
                "portrait secret_probe",
                "portrait secret_probe",
                embedding_directory=str(self.outside),
            )

    def test_unsafe_directory_values_fail_closed_without_filesystem_probes(self) -> None:
        sep = os.sep
        values: list[object] = [
            str(self.outside),
            os.path.relpath(self.outside),
            f"{self.registered}{sep}missing_child{sep}..{sep}..{sep}..{sep}private",
            f"{self.registered.as_posix()}/missing_child/../../../private",
            f"{self.registered}-evil",
            str(self.registered.parent),
            f"{self.registered}{sep}style{sep}a\x01b",
            f"{self.registered}\x00",
            "x" * 5000,
            42,
            b"bytes",
        ]
        if os.name == "nt":
            values.extend(["Z:\\embeddings", "\\\\server\\share\\embeddings"])
        else:
            values.append("/nonexistent-root/embeddings")
        messages = set()
        for value in values:
            with self.subTest(value=repr(value)[:80]):
                messages.add(self._assert_rejected(value))
        self.assertEqual(len(messages), 1)

    def test_empty_directory_is_noop_without_folder_paths_access(self) -> None:
        for value in ("", "   ", None):
            with self.subTest(value=value):
                result = resolver.resolve_textual_inversion_prompt(
                    "portrait registered_style",
                    embedding_directory=value,
                )
                self.assertEqual(result.resolved_text, "portrait registered_style")
        self.assertEqual(self.folder_paths.calls, [])

    def test_registered_root_uses_core_inventory_only(self) -> None:
        values: list[object] = [
            str(self.registered),
            f"{self.registered}{os.sep}",
            self.registered,
            self.registered.as_posix(),
        ]
        if os.name == "nt":
            values.append(str(self.registered).upper())
        for value in values:
            with self.subTest(value=str(value)):
                with _deny_filesystem_probes():
                    result = resolver.resolve_textual_inversion_prompt(
                        "portrait registered_style root_style legacy_model notes",
                        embedding_directory=value,  # type: ignore[arg-type]
                    )
                self.assertEqual(
                    result.resolved_text,
                    "portrait embedding:style/registered_style.pt embedding:root_style.safetensors legacy_model notes",
                )

    def test_registered_subfolder_filters_inventory_with_root_relative_names(self) -> None:
        with _deny_filesystem_probes():
            result = resolver.resolve_textual_inversion_prompt(
                "portrait registered_style root_style",
                embedding_directory=str(self.registered / "style"),
            )
        self.assertEqual(result.resolved_text, "portrait embedding:style/registered_style.pt root_style")

    def test_missing_folder_paths_fails_closed(self) -> None:
        with mock.patch.dict(sys.modules, {"folder_paths": None}):
            with self.assertRaises(ValueError) as caught:
                resolver.resolve_textual_inversion_prompt(
                    "portrait registered_style",
                    embedding_directory=str(self.registered),
                )
        self.assertIn(_REJECTION_FRAGMENT, str(caught.exception))

    def test_node_registered_root_records_root_relative_metadata(self) -> None:
        node = nodes.RookieUIA1111CLIPTextEncode()
        conditioning, = node.encode(
            _FakeClip(),
            "portrait registered_style",
            embedding_directory=str(self.registered),
        )
        self.assertEqual(
            conditioning[0][1]["rookieui_textual_inversion_embeddings"],
            ["embedding:style/registered_style.pt"],
        )

    def test_widget_contract_is_unchanged_for_saved_workflows(self) -> None:
        expected = [
            "steps",
            "a1111_engine",
            "parser",
            "embedding_directory",
            "embedding_names",
            "mean_normalization",
            "use_old_emphasis_implementation",
        ]
        for node_class in (nodes.RookieUIA1111CLIPTextEncode, nodes.RookieUIA1111CLIPTextEncodeSDXL):
            with self.subTest(node=node_class.__name__):
                optional = node_class.INPUT_TYPES()["optional"]
                self.assertEqual(list(optional), expected)
                widget_type, widget_options = optional["embedding_directory"]
                self.assertEqual(widget_type, "STRING")
                self.assertEqual(widget_options["default"], "")


class TranslateLanguageBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.runtime = _fixture_dir(self)
        env = mock.patch.dict(os.environ, {"ROOKIEUI_PROMPT_WORKBENCH_RUNTIME_ROOT": str(self.runtime)})
        env.start()
        self.addCleanup(env.stop)
        self.catalogs = self.runtime / "catalogs"
        self.catalogs.mkdir()
        (self.catalogs / "translation_dictionary.zh-TW.csv").write_text(
            "source,target\nmasterpiece,傑作\n", encoding="utf-8"
        )
        # Lets the traversal also resolve on POSIX, where `..` needs an existing component.
        (self.catalogs / "translation_dictionary.x").mkdir()
        self.secret = self.runtime / "secret.csv"
        self.secret.write_text(f"source,target\nprobe,{_OUTSIDE_VALUE}\n", encoding="utf-8")
        state.update_prompt_workbench_config(
            {"translation": {"default_provider": "csv_tag_dictionary", "providers": {}}}
        )
        app = web.Application()
        registrar = SafeRouteRegistrar(app.router, allowed_prefixes=("/rookieui", "/api/rookieui"))
        for spec in route_spec.AUTHORITATIVE_ROUTE_SPECS:
            if spec.suffix == "/prompt-tools/translate":
                route_spec._register_authoritative_spec(registrar, spec)
        self.client = TestClient(TestServer(app))
        await self.client.start_server()
        self.addAsyncCleanup(self.client.close)

    def _traversal_values(self) -> list[str]:
        values = [
            "x/../../secret",
            "x\\..\\..\\secret",
            "../secret",
            "..",
            ".",
            "en/../../secret",
            "/etc/passwd",
            "C:\\secret",
            "zh-TW.",
            "a" * 40,
            "zh-TW\x00",
        ]
        return values

    def test_service_rejects_traversal_instead_of_reading_outside_csv(self) -> None:
        try:
            result = translation.translate_prompt_workbench_payload(
                {"text": "probe", "to_lang": "x/../../secret", "dictionary_only": True}
            )
        except ValueError:
            return
        self.fail(f"outside CSV disclosed: translated_text={result.translated_text!r} hits={result.dictionary_hits!r}")

    async def test_routes_reject_unsafe_language_tags_on_both_prefixes(self) -> None:
        for prefix in ("/rookieui", "/api/rookieui"):
            for field in ("to_lang", "from_lang"):
                for value in self._traversal_values():
                    with self.subTest(prefix=prefix, field=field, value=value[:20]):
                        response = await self.client.post(
                            f"{prefix}/prompt-tools/translate",
                            json={"text": "probe", field: value, "dictionary_only": True},
                        )
                        body = await response.text()
                        self.assertNotIn(_OUTSIDE_VALUE, body)
                        self.assertEqual(response.status, 400, body[:200])

    def test_rejected_request_never_probes_outside_path(self) -> None:
        touched: list[str] = []
        original_exists = Path.exists
        original_open = Path.open

        def spy_exists(path: Path, *args, **kwargs):
            touched.append(os.path.normcase(os.path.abspath(path)))
            return original_exists(path, *args, **kwargs)

        def spy_open(path: Path, *args, **kwargs):
            touched.append(os.path.normcase(os.path.abspath(path)))
            return original_open(path, *args, **kwargs)

        with mock.patch.object(Path, "exists", spy_exists), mock.patch.object(Path, "open", spy_open):
            with contextlib.suppress(ValueError):
                translation.translate_prompt_workbench_payload(
                    {"text": "probe", "to_lang": "x/../../secret", "dictionary_only": True}
                )
        self.assertNotIn(os.path.normcase(str(self.secret)), touched)

    def test_dictionary_sink_alone_refuses_unsafe_tags(self) -> None:
        for value in self._traversal_values():
            with self.subTest(value=value[:20]):
                paths = translation._translation_dictionary_paths(value)
                self.assertEqual(paths, (self.catalogs / "translation_dictionary.csv",))
        self.assertEqual(
            translation._translation_dictionary_paths("zh-TW"),
            (self.catalogs / "translation_dictionary.zh-TW.csv", self.catalogs / "translation_dictionary.csv"),
        )

    async def test_unexpected_dictionary_failures_return_fixed_detail(self) -> None:
        (self.catalogs / "translation_dictionary.ja.csv").write_bytes(b"source,target\nprobe,\xff\xfeSYNTHETIC\n")
        path_error = PermissionError(13, "synthetic denial", str(self.secret))
        cases = (
            ("decode", None),
            ("oserror", mock.patch.object(translation, "_load_translation_dictionary", side_effect=path_error)),
        )
        for prefix in ("/rookieui", "/api/rookieui"):
            for label, patcher in cases:
                with self.subTest(prefix=prefix, case=label):
                    with patcher or contextlib.nullcontext():
                        response = await self.client.post(
                            f"{prefix}/prompt-tools/translate",
                            json={"text": "probe", "to_lang": "ja", "dictionary_only": True},
                        )
                        payload = await response.json()
                    detail = str(payload.get("detail", ""))
                    self.assertEqual(response.status, 502)
                    self.assertNotIn(str(self.runtime), detail)
                    self.assertNotIn("secret", detail)
                    self.assertNotIn("codec", detail)
                    self.assertEqual(detail, "Prompt-workbench translation failed.")

    async def test_catalog_language_codes_keep_working(self) -> None:
        response = await self.client.post(
            "/rookieui/prompt-tools/translate",
            json={"text": "masterpiece, probe", "from_lang": "auto", "to_lang": "zh-TW", "dictionary_only": True},
        )
        payload = await response.json()
        self.assertEqual(response.status, 200)
        self.assertEqual(payload["translated_text"], "傑作, probe")
        self.assertEqual(payload["to_lang"], "zh-TW")
        for value in ("en", "zh_TW", "pt-BR", "zh-Hant", "es-419"):
            with self.subTest(value=value):
                result = translation.translate_prompt_workbench_payload(
                    {"text": "probe", "to_lang": value, "dictionary_only": True}
                )
                self.assertEqual(result.to_lang, value)
                self.assertNotIn(_OUTSIDE_VALUE, result.translated_text or "")
        default = translation.translate_prompt_workbench_payload({"text": "probe", "dictionary_only": True})
        self.assertEqual((default.from_lang, default.to_lang), ("auto", "en"))


class HostOutputExactNameTests(unittest.TestCase):
    def setUp(self) -> None:
        base = _fixture_dir(self)
        self.output_root = base / "output"
        (self.output_root / "first").mkdir(parents=True)
        (self.output_root / "second").mkdir(parents=True)
        self.literal = self.output_root / "first" / "grid[1].png"
        self.literal.write_bytes(b"literal")
        (self.output_root / "second" / "grid1.png").write_bytes(b"pattern")
        self.outside = base / "outside.png"
        self.outside.write_bytes(b"outside")
        folder_paths = mock.Mock()
        folder_paths.get_output_directory.return_value = str(self.output_root)
        patcher = mock.patch.object(asset_store, "_load_folder_paths_module", return_value=folder_paths)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_bracket_basename_matches_literal_file_only(self) -> None:
        resolved = asset_store.resolve_generated_output_path("grid[1].png")
        self.assertEqual(Path(resolved).read_bytes(), b"literal")

    def test_wildcard_basename_is_not_a_pattern(self) -> None:
        for selector in ("*.png", "grid?.png", "grid[0-9].png", "**"):
            with self.subTest(selector=selector):
                with self.assertRaises(ValueError):
                    asset_store.resolve_generated_output_path(selector)

    def test_case_handling_follows_platform(self) -> None:
        if os.name == "nt":
            self.assertEqual(Path(asset_store.resolve_generated_output_path("GRID[1].PNG")).read_bytes(), b"literal")
        else:
            with self.assertRaises(ValueError):
                asset_store.resolve_generated_output_path("GRID[1].PNG")

    def test_basename_match_resolving_outside_output_root_is_rejected(self) -> None:
        # Deterministic stand-in for a symlink escape on hosts without symlink privilege.
        escape = self.output_root / "second" / "escape.png"
        escape.write_bytes(b"inside")
        original_resolve = Path.resolve

        def resolve(path: Path, *args, **kwargs):
            if path.name == "escape.png" and path.parent.name == "second":
                return original_resolve(self.outside, *args, **kwargs)
            return original_resolve(path, *args, **kwargs)

        with mock.patch.object(Path, "resolve", resolve):
            with self.assertRaises(ValueError):
                asset_store.resolve_generated_output_path("escape.png")

    def test_symlinked_basename_outside_output_root_is_rejected(self) -> None:
        link = self.output_root / "second" / "escape.png"
        try:
            os.symlink(self.outside, link)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink creation unavailable: {type(exc).__name__}")
        with self.assertRaises(ValueError):
            asset_store.resolve_generated_output_path("escape.png")


if __name__ == "__main__":
    unittest.main()
