# E2E Testing SOP

This SOP documents the verified, repeatable steps to run Playwright E2E tests
against a local **test harness** (no live ComfyUI backend required).

Boundary:

- This file covers frontend Playwright harness E2E only.
- Backend low-mock real lanes (`R122`, `R123`) are specified in `tests/TEST_SOP.md`.

## 1. Requirements

- Node.js 18+
- npm 9+
- Python 3.8+ (used by the Playwright web server: `python -m http.server 3000`)
- Playwright browsers installed (`npx playwright install chromium`)

Notes:

- The E2E suite uses `python -m http.server` like ComfyUI-Doctor.
- If your environment only has `python3`, provide a local shim named `python` (see below).
- On WSL running from `/mnt/c/...`, set a writable temp dir to avoid permission issues.

## 2. Verified Procedure

### 2.1 Windows (PowerShell)

```powershell
node -v
npm -v
python --version

npm install
npx playwright install chromium

npm test
```

If port `3000` is blocked/reserved on your machine, set a custom E2E port:

```powershell
$env:OPENCLAW_E2E_PORT = "3300"
npm test
```

### 2.2 WSL2 (bash)

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

# Run with safe temp directory (WSL /mnt/*)
mkdir -p .tmp/playwright
TMPDIR=.tmp/playwright TMP=.tmp/playwright TEMP=.tmp/playwright \
  PATH=".tmp/bin:$PATH" npm test
```

### 2.3 Optional flake-stress mode

Use this when you need to amplify timing-sensitive Playwright failures locally without changing the default `npm test` path.

- Targeted stress run:

```bash
npm run test:stress -- tests/e2e/specs/notifications.spec.js
```

- Override repeat count / workers:

```bash
OPENCLAW_PLAYWRIGHT_REPEAT_EACH=8 \
OPENCLAW_PLAYWRIGHT_STRESS_WORKERS=2 \
  npm run test:stress -- tests/e2e/specs/notifications.spec.js
```

Notes:
- `npm test` remains the default deterministic acceptance path.
- `npm run test:stress` is optional and intended for flake hunting or CI-race investigation.
- The repo-local runner now forwards passthrough Playwright args, so `npm test -- <spec>` and `npm run test:stress -- <spec>` both target specific specs.

## 3. Test Harness Behavior

`tests/e2e/test-harness.html`:

- Creates a minimal mocked ComfyUI environment (`window.app`)
- Mocks `fetch()` for `/openclaw/*` and legacy `/moltbot/*` endpoints (capabilities/health + predictable errors)
- Imports `web/openclaw.js` (the real extension entry) and waits for readiness
- Sets `window.__openclawTestReady = true` and dispatches `openclaw-ready`

## 4. Common Troubleshooting

- If you see `404` / failed module imports for `scripts/app.js`, ensure tests are using the
  Playwright route mock (see `tests/e2e/utils/helpers.js`).
- If tests fail only on WSL `/mnt/c`, use the temp-dir workaround above.

## 5. Transaction-Sensitive Acceptance Addendum

When a change touches a public/admin/webhook/connector or other stateful user-facing flow, the acceptance path must include at least one transaction-level assertion through the relevant surface.

Examples of acceptable transaction-level evidence:
- submit a webhook or connector callback payload and verify the resulting accepted/rejected outcome
- perform an approval or admin action and verify the persisted or rendered result
- submit a model import/download or other state-changing form/action and verify the resulting lifecycle state
- for frontend security fixes, assert the real rendered DOM sink (for example notification text staying escaped instead of becoming live markup), not only fixture/local-storage shape

Non-examples:
- loading the entry page only
- verifying only that a route exists or returns a redirect
- asserting only mocked backend behavior when the production seam is the failure point
