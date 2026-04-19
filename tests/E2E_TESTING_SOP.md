# E2E Testing SOP

This SOP defines the verified Playwright workflow for this repository.

## Scope

- Frontend harness E2E only (Playwright)
- Uses `tests/e2e/test-harness.html` with mocked runtime seams
- Not a live ComfyUI backend integration lane
- Live backend checks are handled separately via `scripts/run_host_embedded_e2e.py`

## Requirements

- Node.js 18+
- npm 9+
- Python command available (`python` or shim to `python3`)
- Playwright Chromium installed (`npx playwright install chromium`)

## Windows (PowerShell)

```powershell
node -v
npm -v
python --version

npm install
npx playwright install chromium
npm test
```

If default port is occupied, override the harness web server port:

```powershell
$env:ROOKIEUI_E2E_PORT = "4300"
npm test
```

For the repo-standard Windows full gate, `scripts/run_full_tests_windows.ps1` now:

- pins Playwright's harness server to the project-local `.venv` Python via `ROOKIEUI_E2E_PYTHON`
- auto-selects a bindable localhost port if `4173` is unavailable
- the Git-Bash repository pre-push path (`.githooks/pre-push -> scripts/pre_push_checks.sh`) now mirrors the same Python/port guardrails before `npm test`

## WSL2 (bash)

```bash
source ~/.nvm/nvm.sh
nvm use 18
node -v
python3 --version

# Provide `python` if only python3 exists
mkdir -p .tmp/bin
ln -sf "$(command -v python3)" .tmp/bin/python

npm install
npx playwright install chromium

mkdir -p .tmp/playwright
TMPDIR=.tmp/playwright TMP=.tmp/playwright TEMP=.tmp/playwright \
  PATH=".tmp/bin:$PATH" npm test
```

If default port is occupied:

```bash
ROOKIEUI_E2E_PORT=4300 npm test
```

## Harness Behavior

- Serves repository root via `python -m http.server`
- Loads `tests/e2e/test-harness.html`
- Imports real extension entry and waits for readiness signal
- Uses mocked network routes for deterministic E2E execution

## Troubleshooting

- `python: command not found` on WSL:
  - create local shim (`.tmp/bin/python`) as above
- Port bind failure:
  - set `ROOKIEUI_E2E_PORT` to an unused port
- Windows full-gate drift (`npm test` starts harness with the wrong Python):
  - prefer `powershell -File scripts/run_full_tests_windows.ps1`
  - or set `ROOKIEUI_E2E_PYTHON=.venv\Scripts\python.exe` before `npm test`
- Browser missing:
  - run `npx playwright install chromium`
- Dependency drift:
  - remove `node_modules` and rerun `npm install`

## Optional Host-Embedded E2E Contract

Use this only when backend/runtime regressions are suspected (for example, preset-driven loader mismatches).

```bash
python scripts/run_host_embedded_e2e.py
```

Strict report-only contract pass:

```bash
python scripts/run_host_embedded_e2e.py --skip-execute
```
