from __future__ import annotations

from pathlib import Path
import shutil
import unittest

from rookieui.services.textual_inversion_resolver import (
    resolve_textual_inversion_prompt,
    scan_textual_inversion_embeddings,
)


class TextualInversionResolverTests(unittest.TestCase):
    def test_scan_textual_inversion_embeddings_collects_relative_files(self) -> None:
        root = Path(".tmp") / "test_textual_inversion_resolver"
        if root.exists():
            shutil.rmtree(root)
        try:
            (root / "style").mkdir(parents=True)
            (root / "style" / "badhandv4.pt").write_bytes(b"not loaded by scanner")
            (root / "ignore.txt").write_text("ignored", encoding="utf-8")

            names = scan_textual_inversion_embeddings(root)

            self.assertEqual(names, ["style/badhandv4.pt"])
        finally:
            if root.exists():
                shutil.rmtree(root)

    def test_resolve_textual_inversion_prompt_handles_aliases_and_fix_metadata(self) -> None:
        result = resolve_textual_inversion_prompt(
            "portrait badhandv4 embedding:style/badhandv4",
            embedding_names=["style/badhandv4.pt::vectors=3"],
        )

        self.assertEqual(
            result.resolved_text,
            "portrait embedding:style/badhandv4.pt embedding:style/badhandv4.pt",
        )
        self.assertEqual([reference.syntax for reference in result.references], ["explicit", "bare"])
        self.assertEqual([reference.canonical_token for reference in result.references], ["embedding:style/badhandv4.pt"] * 2)
        self.assertEqual(
            [fix.to_payload() for fix in result.fixes],
            [
                {"offset": 1, "name": "style/badhandv4.pt", "token": "embedding:style/badhandv4.pt", "vectors": 3},
                {"offset": 2, "name": "style/badhandv4.pt", "token": "embedding:style/badhandv4.pt", "vectors": 3},
            ],
        )

    def test_resolve_textual_inversion_prompt_reports_missing_explicit_embedding(self) -> None:
        result = resolve_textual_inversion_prompt(
            "portrait embedding:missing_style dramatic light",
            embedding_names=["badhandv4.pt"],
        )

        self.assertEqual(result.resolved_text, "portrait missing_style dramatic light")
        self.assertEqual(len(result.references), 1)
        self.assertFalse(result.references[0].exists)
        self.assertEqual(result.references[0].canonical_token, "missing_style")
        self.assertEqual(list(result.missing_tokens), ["embedding:missing_style"])

    def test_resolve_textual_inversion_prompt_honors_sdxl_channel_filters(self) -> None:
        global_result = resolve_textual_inversion_prompt(
            "portrait local_style",
            embedding_names=["local_style.safetensors::vectors=2::channels=clip_l"],
            channel="clip_g",
        )
        local_result = resolve_textual_inversion_prompt(
            "portrait local_style",
            embedding_names=["local_style.safetensors::vectors=2::channels=clip_l"],
            channel="clip_l",
        )

        self.assertEqual(global_result.resolved_text, "portrait local_style")
        self.assertEqual(list(global_result.channel_mismatch_tokens), ["local_style"])
        self.assertEqual(local_result.resolved_text, "portrait embedding:local_style.safetensors")
        self.assertEqual(local_result.references[0].vectors, 2)
        self.assertEqual(local_result.fixes[0].vectors, 2)


if __name__ == "__main__":
    unittest.main()
