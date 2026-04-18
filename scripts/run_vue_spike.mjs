import { rmSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";
import { build, preview } from "vite";

const repoRoot = resolve(fileURLToPath(new URL(".", import.meta.url)), "..");
const configFile = resolve(repoRoot, "spikes", "vue", "vite.config.mjs");
const outDir = resolve(repoRoot, ".tmp", "vue-spike-dist");
const previewPort = 4175;

function printDecision({ decision, summary, issues = [] }) {
  console.log(`[vue-spike] decision=${decision}`);
  console.log(`[vue-spike] summary=${summary}`);
  for (const issue of issues) {
    console.log(`[vue-spike] issue=${issue}`);
  }
}

async function main() {
  let previewServer;
  let browser;
  let decision = {
    decision: "defer",
    summary: "The Vue host-adapter spike did not complete enough coexistence checks to justify further migration work.",
    issues: [],
  };

  try {
    rmSync(outDir, { recursive: true, force: true });

    console.log("[vue-spike] build");
    await build({ configFile, logLevel: "info" });

    console.log("[vue-spike] preview");
    previewServer = await preview({
      configFile,
      logLevel: "info",
      preview: {
        host: "127.0.0.1",
        port: previewPort,
        strictPort: true,
      },
    });

    const browserUrl =
      previewServer.resolvedUrls?.local?.[0] ?? `http://127.0.0.1:${previewPort}/`;
    console.log(`[vue-spike] browser=${browserUrl}`);

    browser = await chromium.launch();
    const page = await browser.newPage();
    const consoleErrors = [];
    const pageErrors = [];
    page.on("console", (message) => {
      console.log(`[vue-spike][console:${message.type()}] ${message.text()}`);
      if (message.type() === "error") {
        consoleErrors.push(message.text());
      }
    });
    page.on("pageerror", (error) => {
      console.log(`[vue-spike][pageerror] ${error.message}`);
      pageErrors.push(error.message);
    });

    await page.goto(browserUrl, { waitUntil: "networkidle" });
    await page.waitForSelector('[data-testid="vue-spike-root"]', { state: "attached" });
    await page.waitForSelector('[data-testid="vue-extension-panel"]', { state: "attached" });
    await page.waitForFunction(() => {
      const panel = document.querySelector('[data-testid="vue-extension-panel"]');
      return Boolean(panel?.textContent?.includes("f72-20260418"));
    });

    await page.getByTestId("tab-custom").click();
    await page.waitForFunction(() => {
      const panel = document.querySelector('[data-testid="custom-extension-panel"]');
      return Boolean(panel?.textContent?.includes("Existing Custom Extension"));
    });

    await page.getByTestId("tab-vue").click();
    await page.waitForSelector('[data-testid="vue-extension-panel"]', { state: "attached" });

    const lifecycle = await page.evaluate(() => ({
      customUnmounts: window.__ROOKIEUI_VUE_SPIKE__?.lifecycle?.customUnmounts ?? 0,
      vueMounts: window.__ROOKIEUI_VUE_SPIKE__?.lifecycle?.vueMounts ?? 0,
    }));

    const compatibilityIssues = [...consoleErrors, ...pageErrors];
    if (compatibilityIssues.length > 0) {
      decision = {
        decision: "defer",
        summary:
          "The Vue host-adapter spike mounted, but runtime console/page errors still make the coexistence proof too noisy for a reliable decision.",
        issues: compatibilityIssues,
      };
    } else if (lifecycle.customUnmounts < 1 || lifecycle.vueMounts < 1) {
      decision = {
        decision: "defer",
        summary:
          "The Vue host-adapter spike did not demonstrate the expected mount/unmount lifecycle guarantees for coexistence.",
        issues: [
          `Observed lifecycle counts: customUnmounts=${lifecycle.customUnmounts}, vueMounts=${lifecycle.vueMounts}`,
        ],
      };
    } else {
      decision = {
        decision: "keep-exploring",
        summary:
          "The Vue host-adapter spike mounted a Vue extension and preserved custom-extension coexistence against the same RookieUI bootstrap contract without changing production entrypoints.",
        issues: [],
      };
    }

    printDecision(decision);
  } finally {
    if (browser) {
      await browser.close();
    }
    if (previewServer?.httpServer) {
      await new Promise((resolveClose, rejectClose) => {
        previewServer.httpServer.close((error) => {
          if (error) {
            rejectClose(error);
            return;
          }
          resolveClose();
        });
      });
    }
    rmSync(outDir, { recursive: true, force: true });
  }
}

main().catch((error) => {
  printDecision({
    decision: "defer",
    summary: "The Vue host-adapter spike hit a tooling/runtime failure before coexistence checks completed.",
    issues: [error instanceof Error ? error.message : String(error)],
  });
  process.exitCode = 0;
});
