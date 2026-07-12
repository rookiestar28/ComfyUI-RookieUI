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

### Problem-First Test Design Rule (Mandatory)

All test scripts, test harnesses, and validation flows must be designed first to reproduce real failures and catch bugs early.

The purpose of testing is to expose defects, regressions, drift, and broken assumptions before users hit them. Tests must not be designed merely to produce a green validation result, satisfy a checklist, or prove that a happy path still passes. Do not waste validation time on pass-only checks that cannot fail for the bug class under review.

Every bugfix or high-risk change must start from the question: "Which test would have caught this before release?" If the existing gate missed the bug, update the targeted test or SOP flow so the same class of bug fails deterministically next time.

Required minimum gate:

1. `pre-commit run detect-secrets --all-files`
2. `pre-commit run --all-files --show-diff-on-failure`
3. prompt compiler guard tests for A1111 node/workflow double-compilation regressions
4. backend unit tests (`scripts/run_unittests.py`)
5. frontend tests (`npm test`)
6. targeted frontend type validation for TS-first seams (`npm run test:types`) when the change touches the typed frontend foundation
Optional (recommended for runtime/host-integration changes):

7. host-embedded E2E lane (`scripts/run_host_embedded_e2e.py`, which delegates to `scripts/run_live_smoke_tests.py`)

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

These wrappers are the final sweep gate. For bugfixes or high-risk changes, run and record
the targeted reproduce/pin checks first, then use the wrapper to prove whole-repo stability.

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
npm ci
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
- The repository full-test wrappers verify every declared top-level Node dependency
  against the exact `package-lock.json` version before testing. A missing or stale
  install is repaired with `npm ci` and verified again; package-marker existence is
  not sufficient validation.
- After dependency identity is established, full-test wrappers run
  `npm run audit:ci`. The complete production/dev and direct/transitive graph is
  reported; high or critical advisories fail validation. Do not omit dependency
  classes, disable audit, force a resolution, or convert an audit failure to success.
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
