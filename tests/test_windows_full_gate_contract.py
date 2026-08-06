from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class WindowsFullGateContractTests(unittest.TestCase):
    def test_checked_native_commands_preserve_stderr_without_false_failure(self) -> None:
        wrapper = (ROOT / "scripts/run_full_tests_windows.ps1").read_text(encoding="utf-8")
        start = wrapper.index("function Invoke-Checked")
        end = wrapper.index("function Test-PortBindable", start)
        helper = wrapper[start:end]

        self.assertIn("function Invoke-NativeCapture", wrapper)
        self.assertIn('$ErrorActionPreference = "Continue"', wrapper)
        self.assertIn("$commandOutput = @(& $Command 2>&1)", wrapper)
        self.assertIn("$commandExitCode = $LASTEXITCODE", wrapper)
        self.assertIn("Write-Host $outputLine", wrapper)
        self.assertIn("$commandExitCode = Invoke-NativeCapture -Command $Command -ReplayOutput", helper)
        self.assertIn("if ($commandExitCode -ne 0)", helper)

        dependency_check = "Invoke-NativeCapture -Command { & node scripts\\verify_node_modules_lock.mjs } -ReplayOutput"
        self.assertIn(dependency_check, wrapper)


if __name__ == "__main__":
    unittest.main()
