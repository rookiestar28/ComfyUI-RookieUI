// @ts-check
const { defineConfig } = require("@playwright/test");

const e2ePort = process.env.ROOKIEUI_E2E_PORT || "4173";
const e2eBase = `http://127.0.0.1:${e2ePort}`;
// CRITICAL: keep the Playwright harness Python configurable so repo test scripts can pin
// the project-local venv interpreter; falling back to arbitrary global Python causes Windows drift.
const pythonCmd = process.env.ROOKIEUI_E2E_PYTHON || process.env.PYTHON || "python";

module.exports = defineConfig({
  testDir: "tests/e2e/specs",
  timeout: 30000,
  retries: 0,
  use: {
    baseURL: `${e2eBase}/tests/e2e/`,
    headless: true,
  },
  webServer: {
    command: `${pythonCmd} -m http.server ${e2ePort} --bind 127.0.0.1 --directory .`,
    url: `${e2eBase}/tests/e2e/test-harness.html`,
    reuseExistingServer: true,
    timeout: 30000,
  },
});
