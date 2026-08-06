from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class WindowsFullGateContractTests(unittest.TestCase):
    def test_checked_native_commands_preserve_stderr_without_false_failure(self) -> None:
        wrapper = (ROOT / "scripts/run_full_tests_windows.ps1").read_text(encoding="utf-8")
        start = wrapper.index("function Invoke-Checked")
        end = wrapper.index("function Test-PortBindable", start)
        helper = wrapper[start:end]

        self.assertIn('$ErrorActionPreference = "Continue"', helper)
        self.assertIn("$commandOutput = @(& $Command 2>&1)", helper)
        self.assertIn("$commandExitCode = $LASTEXITCODE", helper)
        self.assertIn("Write-Host $outputLine", helper)
        self.assertIn("if ($commandExitCode -ne 0)", helper)


if __name__ == "__main__":
    unittest.main()
