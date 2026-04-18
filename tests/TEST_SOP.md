# Test SOP

This document is the source-of-truth local verification workflow for **ComfyUI-RookieUI**.
Use it before push and before marking any implementation as accepted.

## Scope

- Frontend Playwright harness E2E and frontend unit tests via `npm test`
- Frontend static type validation via `npm run test:types`
- Backend Python unit tests via `scripts/run_unittests.py`
- Repository hygiene checks via `pre-commit`

## Required Reading Order

1. `tests/TEST_SOP.md`
2. `tests/E2E_TESTING_NOTICE.md`
3. `tests/E2E_TESTING_SOP.md`

## Acceptance Rule

A change is not accepted until required checks pass and evidence is recorded.

Required minimum gate:

1. `pre-commit run detect-secrets --all-files`
2. `pre-commit run --all-files --show-diff-on-failure`
3. backend unit tests (`scripts/run_unittests.py`)
4. frontend tests (`npm test`)
5. targeted frontend type validation for TS-first seams (`npm run test:types`) when the change touches the typed frontend foundation
Optional (recommended for runtime/host-integration changes):

6. host-embedded E2E lane (`scripts/run_host_embedded_e2e.py`, which delegates to `scripts/run_live_smoke_tests.py`)

### Bugfix/Hotfix Rule (Reproduce -> Pin -> Sweep)

For bugfix/hotfix work, acceptance evidence must include:

1. pre-fix reproduction evidence
2. post-fix targeted regression evidence
3. final full-gate evidence

### Documentation-only Exception

If all touched files are documentation/planning text only (no code/tests/scripts/config/runtime changes), full test execution is optional.

## Prerequisites

- Python 3.10+
- Node.js 18+
- npm 9+
- `pre-commit` available in the interpreter used for checks

Recommended venv paths:

- Windows: `.venv`
- WSL/Linux: `.venv-wsl` (or `.venv` if you do not use dual-OS workflow)

## Quick Start (One-command full gate)

### Windows (PowerShell)

```powershell
powershell -File scripts/run_full_tests_windows.ps1
```

### Linux / WSL (bash)

```bash
bash scripts/run_full_tests_linux.sh
```

Enable optional host-embedded E2E lane in either wrapper script:

- PowerShell:

```powershell
$env:ROOKIEUI_RUN_LIVE_SMOKE = "1"
powershell -File scripts/run_full_tests_windows.ps1
```

- bash:

```bash
ROOKIEUI_RUN_LIVE_SMOKE=1 bash scripts/run_full_tests_linux.sh
```

## Optional Automation (Git pre-push hook)

Enable repository-managed hooks once:

```bash
git config core.hooksPath .githooks
```

After that, every `git push` will run:

```bash
bash scripts/pre_push_checks.sh
```

## Manual Staged Workflow (CI-parity)

Use this if you need explicit per-stage execution.

1. Detect secrets:

```bash
pre-commit run detect-secrets --all-files
```

2. Run all hooks:

```bash
pre-commit run --all-files --show-diff-on-failure
```

Important: if hooks auto-fix files, review/stage/commit those changes, then rerun until clean.

3. Backend unit tests:

```bash
MOLTBOT_STATE_DIR="$(pwd)/moltbot_state/_local_unit" \
  python scripts/run_unittests.py --start-dir tests --pattern "test_*.py"
```

4. Frontend tests:

```bash
node -v
npm install
npx playwright install chromium
npm run test:types
npm test
```

5. Optional host-embedded E2E lane (recommended for runtime/host-integration changes):

```bash
python scripts/run_host_embedded_e2e.py
```

Strict report-only contract pass:

```bash
python scripts/run_host_embedded_e2e.py --skip-execute
```

Optional base URL override:

```bash
ROOKIEUI_LIVE_BASE_URL=http://127.0.0.1:8188 python scripts/run_host_embedded_e2e.py
```

## Environment Guardrails

- Keep Python interpreter consistent across all commands.
- Do not mix global and venv-installed `pre-commit` accidentally.
- Node must be 18+ before `npm test`.
- On Windows, prefer repo-local `PRE_COMMIT_HOME` to avoid cache lock issues.
- On WSL, if `python` command is missing but `python3` exists, create a local shim (see E2E SOP).

## Evidence Recording

Implementation records must include:

- date/time
- OS/environment
- command log reference
- pass/fail result for each required stage
