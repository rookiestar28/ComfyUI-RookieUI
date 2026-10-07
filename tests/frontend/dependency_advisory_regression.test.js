import { afterEach, describe, expect, test, vi } from "vitest";
import { h } from "vue";
import { renderToString } from "@vue/server-renderer";
import sourceMap from "source-map-js";

describe("dependency input safety", () => {
  afterEach(() => vi.restoreAllMocks());

  test("SSR rejects carriage returns in attribute names while preserving valid attributes", async () => {
    vi.spyOn(console, "warn").mockImplementation(() => {});
    vi.spyOn(console, "error").mockImplementation(() => {});
    const output = await renderToString(h("div", {
      "data-label": "synthetic",
      "data-label\rdata-injected": "synthetic",
    }));
    expect(output).toContain('data-label="synthetic"');
    expect(output).not.toContain("\r");
    expect(output).not.toContain("data-injected");
  });

  test("indexed source maps reject invalid offsets without traversing mappings", () => {
    const map = { version: 3, sources: ["synthetic.js"], names: [], mappings: "AAAA" };
    const valid = new sourceMap.SourceMapConsumer({
      version: 3, sections: [{ offset: { line: 0, column: 0 }, map }],
    });
    expect(valid.sources).toEqual(["synthetic.js"]);
    // Constructor-only invalid input: never traverse or allocate offset lines.
    expect(() => new sourceMap.SourceMapConsumer({
      version: 3, sections: [{ offset: { line: Infinity, column: 0 }, map }],
    })).toThrow();
  });
});
