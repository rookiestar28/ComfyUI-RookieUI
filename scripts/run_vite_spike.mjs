import { rmSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";
import { build, preview } from "vite";

const repoRoot = resolve(fileURLToPath(new URL(".", import.meta.url)), "..");
const configFile = resolve(repoRoot, "spikes", "vite", "vite.config.mjs");
const outDir = resolve(repoRoot, ".tmp", "vite-spike-dist");
const previewPort = 4174;

function printDecision({ decision, summary, issues = [] }) {
  console.log(`[vite-spike] decision=${decision}`);
  console.log(`[vite-spike] summary=${summary}`);
  for (const issue of issues) {
    console.log(`[vite-spike] issue=${issue}`);
  }
}

async function main() {
  let previewServer;
  let browser;
  let decision = {
    decision: "defer",
    summary: "The Vite spike did not complete enough runtime checks to justify a default-path switch.",
    issues: [],
  };
  try {
    rmSync(outDir, { recursive: true, force: true });

    console.log("[vite-spike] build");
    await build({ configFile, logLevel: "info" });

    console.log("[vite-spike] preview");
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
    console.log(`[vite-spike] browser=${browserUrl}`);

    browser = await chromium.launch();
    const page = await browser.newPage();
    const consoleErrors = [];
    const pageErrors = [];
    page.on("console", (message) => {
      console.log(`[vite-spike][console:${message.type()}] ${message.text()}`);
      if (message.type() === "error") {
        consoleErrors.push(message.text());
      }
    });
    page.on("pageerror", (error) => {
      console.log(`[vite-spike][pageerror] ${error.message}`);
      pageErrors.push(error.message);
    });
    await page.goto(browserUrl, { waitUntil: "networkidle" });
    await page.waitForSelector("#mock-sidebar-tabs", { state: "attached" });
    try {
      await page.waitForFunction(() => {
        const root = document.getElementById("rookieui-root");
        const sidebar = document.getElementById("mock-sidebar-tabs");
        return (
          Boolean(root?.textContent?.trim()) &&
          Boolean(sidebar?.textContent?.includes("Txt2Img"))
        );
      });
      decision = {
        decision: "keep-exploring",
        summary:
          "The bounded Vite spike built successfully and mounted the RookieUI shell in a preview runtime without changing production entrypoints.",
        issues: [],
      };
    } catch (error) {
      const compatibilityIssues = [...consoleErrors, ...pageErrors];
      decision = {
        decision: "defer",
        summary:
          "The bounded Vite spike builds, but the preview runtime does not currently mount RookieUI cleanly enough for a low-risk default-path migration.",
        issues:
          compatibilityIssues.length > 0
            ? compatibilityIssues
            : [error instanceof Error ? error.message : String(error)],
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
    summary: "The Vite spike hit a tooling/runtime compatibility failure before the bounded preview check completed.",
    issues: [error instanceof Error ? error.message : String(error)],
  });
  process.exitCode = 0;
});
