from __future__ import annotations

from pathlib import Path
import unittest

from rookieui.contracts.family_template_manifest import (
    OFFICIAL_TEMPLATE_GALLERY_JSON_DEFERRED_SURFACE_MARKERS,
    OFFICIAL_TEMPLATE_GALLERY_JSON_REMOVED_MARKERS,
)
from rookieui.contracts.model_family_registry import list_model_family_registry_entries
from rookieui.services.presets import build_preset_payload


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _public_doc_paths() -> list[Path]:
    docs_root = ROOT / "docs"
    paths = [README]
    if docs_root.exists():
        paths.extend(
            sorted(
                path
                for path in docs_root.rglob("*")
                if path.is_file() and path.suffix.lower() in {".md", ".rst", ".txt"}
            )
        )
    return paths


class PublicDocsTruthfulnessTests(unittest.TestCase):
    def test_public_docs_use_the_current_official_template_source_basis(self) -> None:
        for path in _public_doc_paths():
            text = _read_text(path)
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertNotIn("`comfyui-workflow-templates` 0.11.2", text)
        self.assertIn("`comfyui-workflow-templates` 0.11.6", _read_text(README))

    def test_readme_lists_accepted_local_ideogram_and_krea_txt2img_profiles(self) -> None:
        text = _read_text(README)
        shipped_profile_line = next(
            line
            for line in text.splitlines()
            if "RookieUI ships official ComfyUI template-backed txt2img presets" in line
        )

        self.assertIn("Local `Ideogram v4` and `Krea-2 Turbo` txt2img workflows", text)
        self.assertIn("`Ideogram v4`", shipped_profile_line)
        self.assertIn("`Krea-2 Turbo`", shipped_profile_line)
        self.assertIn("official encoder/model/LoRA prerequisites", text)

    def test_readme_defers_api_provider_and_style_reference_workflows_only(self) -> None:
        text = _read_text(README)

        self.assertIn(
            "API-provider Ideogram/Krea workflows and Krea style-reference workflow remain unsupported",
            text,
        )
        for line in text.splitlines():
            if "deferred" in line.lower() or "follow-up" in line.lower():
                with self.subTest(line=line):
                    self.assertNotIn("Ideogram v4", line)
                    self.assertNotIn("Krea-2 Turbo", line)

    def test_public_docs_do_not_expose_internal_evidence_paths(self) -> None:
        forbidden_fragments = (
            ".planning/",
            ".planning\\",
            "reference/docs/",
            "reference\\docs\\",
            "reference/comfyui/",
            "reference\\comfyui\\",
            "_COMMAND_LOG",
            "_IMPLEMENTATION_RECORD",
            "_PLAN.md",
            "ROADMAP.md",
            "260707-",
        )

        for path in _public_doc_paths():
            text = _read_text(path)
            for fragment in forbidden_fragments:
                with self.subTest(path=path.relative_to(ROOT), fragment=fragment):
                    self.assertNotIn(fragment, text)

    def test_deferred_or_removed_gallery_ids_are_not_supported_profile_ids(self) -> None:
        unsupported_gallery_ids = set(OFFICIAL_TEMPLATE_GALLERY_JSON_DEFERRED_SURFACE_MARKERS)
        unsupported_gallery_ids.update(OFFICIAL_TEMPLATE_GALLERY_JSON_REMOVED_MARKERS)
        supported_ids = {entry.id for entry in list_model_family_registry_entries()}
        supported_ids.update(preset["id"] for preset in build_preset_payload()["presets"])

        self.assertIn("api_ideogram_v4_t2i", unsupported_gallery_ids)
        self.assertIn("api_krea2_t2i", unsupported_gallery_ids)
        self.assertIn("api_krea2_style_reference", unsupported_gallery_ids)
        self.assertIn("api_ideogram_v3_t2i", unsupported_gallery_ids)
        self.assertFalse(unsupported_gallery_ids & supported_ids)
