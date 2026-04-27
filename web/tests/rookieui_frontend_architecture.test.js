import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";

import { describe, expect, test } from "vitest";

import { ROOKIEUI_ASSET_REVISION } from "../rookieui_asset_revision.js";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");

function readFile(relativePath) {
  return fs.readFileSync(path.join(repoRoot, relativePath), "utf8");
}

function countLines(relativePath) {
  return readFile(relativePath).split(/\r?\n/).length;
}

function listShippedFrontendFiles(rootDir) {
  const collected = [];
  const walk = (currentDir) => {
    for (const entry of fs.readdirSync(currentDir, { withFileTypes: true })) {
      const absolutePath = path.join(currentDir, entry.name);
      const relativePath = path.relative(repoRoot, absolutePath).replace(/\\/g, "/");
      if (entry.isDirectory()) {
        if (relativePath === "web/tests") {
          continue;
        }
        walk(absolutePath);
        continue;
      }
      if (!/\.(js|css)$/i.test(entry.name)) {
        continue;
      }
      if (relativePath === "web/rookieui_asset_revision.js") {
        continue;
      }
      collected.push(relativePath);
    }
  };
  walk(rootDir);
  return collected.sort();
}

function computeShippedFrontendFingerprint() {
  const webRoot = path.join(repoRoot, "web");
  const hash = crypto.createHash("sha1");
  for (const relativePath of listShippedFrontendFiles(webRoot)) {
    hash.update(relativePath);
    hash.update("\0");
    hash.update(readFile(relativePath));
    hash.update("\0");
  }
  return hash.digest("hex").slice(0, 10);
}

describe("frontend architecture guardrails", () => {
  test("keeps revision-token ownership out of shipped import specifiers", () => {
    const webRoot = path.join(repoRoot, "web");
    const allFiles = fs.readdirSync(webRoot, { recursive: true }).filter((entry) => String(entry).endsWith(".js"));
    const versionedImportFiles = [];
    for (const relativeEntry of allFiles) {
      const relativePath = path.join("web", String(relativeEntry));
      const source = readFile(relativePath);
      if (/from\s+["'][^"']+\?v=/.test(source) || /import\s*\(\s*["'][^"']+\?v=/.test(source)) {
        versionedImportFiles.push(relativePath);
      }
    }
    expect(versionedImportFiles).toEqual([]);
  });

  test("keeps sidebar shell within the modularization size budget", () => {
    // IMPORTANT: this budget is the regression tripwire for R67; if the shell grows past it, extract another service seam instead of accreting helpers back into the monolith.
    expect(countLines("web/rookieui_sidebar_shell.js")).toBeLessThanOrEqual(1700);
  });

  test("keeps Prompt Workbench shell behind extracted module ownership boundaries", () => {
    // IMPORTANT: this budget prevents prompt-all-in-one parity work from sliding back into a single closure-heavy frontend file.
    const shellPath = "web/sidebar_tabs/rookieui_prompt_workbench_shell.js";
    const shellSource = readFile(shellPath);
    const extractedModules = [
      "web/sidebar_tabs/prompt_workbench/rookieui_prompt_workbench_i18n.js",
      "web/sidebar_tabs/prompt_workbench/rookieui_prompt_workbench_tokens.js",
      "web/sidebar_tabs/prompt_workbench/rookieui_prompt_workbench_catalog.js",
    ];

    expect(countLines(shellPath)).toBeLessThanOrEqual(3100);
    extractedModules.forEach((relativePath) => {
      expect(fs.existsSync(path.join(repoRoot, relativePath))).toBe(true);
    });
    expect(shellSource).toContain("./prompt_workbench/rookieui_prompt_workbench_i18n.js");
    expect(shellSource).toContain("./prompt_workbench/rookieui_prompt_workbench_tokens.js");
    expect(shellSource).toContain("./prompt_workbench/rookieui_prompt_workbench_catalog.js");
    expect(shellSource).not.toMatch(/const\s+WORKBENCH_I18N\s*=/);
    expect(shellSource).not.toMatch(/function\s+splitPromptTokenText\s*\(/);
    expect(shellSource).not.toMatch(/function\s+normalizeGroupTagEntry\s*\(/);
  });

  test("keeps the bootstrap entrypoint and feature registry within phase-59 size budgets", () => {
    // IMPORTANT: these budgets protect the phase-59 bootstrap split; if either file grows past budget,
    // extract another registry/helper seam instead of rebuilding a bootstrap monolith.
    expect(countLines("web/rookieui_extension.js")).toBeLessThanOrEqual(220);
    expect(countLines("web/rookieui_feature_registry.js")).toBeLessThanOrEqual(180);
  });

  test("pins asset revision token to the shipped frontend fingerprint", () => {
    // IMPORTANT: this is the cache-busting tripwire; if shipped frontend modules change without a new revision suffix, live hosts can silently keep serving stale code.
    const expectedFingerprint = computeShippedFrontendFingerprint();
    expect(ROOKIEUI_ASSET_REVISION).toMatch(new RegExp(`-h${expectedFingerprint}$`));
  });
});
