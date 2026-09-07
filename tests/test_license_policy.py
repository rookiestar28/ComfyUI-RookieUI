from __future__ import annotations

import hashlib
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_AGPL_NORMALIZED_SHA256 = (
    "0d96a4ff68ad6d4b6f1f30f713b18d5184912ba8dd389f86aa7710db079abcb0"  # pragma: allowlist secret
)


class LicensePolicyTests(unittest.TestCase):
    def test_license_is_the_unmodified_official_agpl_v3_text(self) -> None:
        text = (ROOT / "LICENSE").read_text(encoding="utf-8-sig").replace("\r\n", "\n")

        self.assertEqual(
            hashlib.sha256(text.encode("utf-8")).hexdigest(),
            OFFICIAL_AGPL_NORMALIZED_SHA256,
        )
        self.assertTrue(text.startswith("                    GNU AFFERO GENERAL PUBLIC LICENSE\n"))
        self.assertIn("                       Version 3, 19 November 2007\n", text)
        self.assertIn("                     END OF TERMS AND CONDITIONS\n", text)
        self.assertNotIn("Project source copyright notice", text)

    def test_public_metadata_remains_agpl_and_has_no_misspelled_owner(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("GNU Affero General Public License v3.0 (AGPL-3.0)", readme)

        misspelled_owner = "rooi" + "estar28"
        completed = subprocess.run(
            ["git", "grep", "-n", misspelled_owner, "--", ":(exclude).planning/**", ":(exclude)reference/**"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(completed.returncode, 1, completed.stdout)


if __name__ == "__main__":
    unittest.main()
