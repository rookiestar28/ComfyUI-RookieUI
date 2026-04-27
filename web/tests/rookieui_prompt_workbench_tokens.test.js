import { describe, expect, test } from "vitest";

import {
  adjustPromptTokenWeight,
  buildPromptTextFromTokens,
  normalizePromptEntry,
  parsePromptTokens,
  serializeTokenPayload,
  splitPromptTokenText,
} from "../sidebar_tabs/prompt_workbench/rookieui_prompt_workbench_tokens.js";

describe("Prompt Workbench token module", () => {
  test("splits prompt text without breaking weighted, schedule, or network tokens", () => {
    const source = "masterpiece, (best quality:1.2), <lora:detail,helper:0.8>, [smile:serious:0.4]\nBREAK";

    expect(splitPromptTokenText(source)).toEqual([
      "masterpiece",
      "(best quality:1.2)",
      "<lora:detail,helper:0.8>",
      "[smile:serious:0.4]",
      "BREAK",
    ]);

    const tokens = parsePromptTokens(source, { scope: "prompt" });
    expect(tokens.map((token) => token.keyword_family)).toEqual(["plain", "weighted", "lora", "schedule", "break"]);
    expect(buildPromptTextFromTokens(tokens)).toBe(
      "masterpiece, (best quality:1.2), <lora:detail,helper:0.8>, [smile:serious:0.4], BREAK",
    );
  });

  test("serializes persisted token payloads and adjusts token weights", () => {
    const [token] = parsePromptTokens("cinematic lighting", { scope: "negative" });
    token.disabled = true;
    token.selected = true;
    token.translated_text = "電影光";

    expect(serializeTokenPayload(token, 3, "negative")).toEqual({
      raw_text: "cinematic lighting",
      normalized_text: "cinematic lighting",
      scope: "negative",
      order_index: 0,
      disabled: true,
      selected: true,
      translated_text: "電影光",
      keyword_family: "plain",
      weight: 0,
    });
    expect(adjustPromptTokenWeight("cinematic lighting", 0.1)).toBe("(cinematic lighting:1.1)");
    expect(adjustPromptTokenWeight("(cinematic lighting:1.2)", -0.1)).toBe("(cinematic lighting:1.1)");
  });

  test("normalizes saved prompt entries with valid persisted token payloads only", () => {
    const entry = normalizePromptEntry({
      id: "favorite-1",
      label: "Favorite",
      prompt_text: "masterpiece",
      tag_tokens: ["masterpiece", ""],
      token_payloads: [{ raw_text: "masterpiece", keyword_family: "plain" }, { raw_text: "" }],
      created_at: 42,
    });

    expect(entry.tag_tokens).toEqual(["masterpiece"]);
    expect(entry.token_payloads).toHaveLength(1);
    expect(entry.token_payloads[0].raw_text).toBe("masterpiece");
  });
});
