import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, test } from "vitest";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");

function readFile(relativePath) {
  return fs.readFileSync(path.join(repoRoot, relativePath), "utf8");
}

function countLines(relativePath) {
  return readFile(relativePath).split(/\r?\n/).length;
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
});
