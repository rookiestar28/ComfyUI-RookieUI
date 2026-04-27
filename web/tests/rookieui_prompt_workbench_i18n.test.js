import { describe, expect, test } from "vitest";

import {
  computeLanguageSelectorPlacement,
  createWorkbenchLanguageSupport,
  formatLanguageOptionLabel,
} from "../sidebar_tabs/prompt_workbench/rookieui_prompt_workbench_i18n.js";

describe("Prompt Workbench i18n module", () => {
  test("normalizes language aliases and follows fallback-code chains for UI copy", () => {
    const support = createWorkbenchLanguageSupport([
      { code: "en", title: "English", native_title: "English" },
      { code: "zh-CN", title: "Simplified Chinese", native_title: "简体中文", aliases: ["zh_CN"], fallback_code: "en" },
      { code: "zh-TW", title: "Traditional Chinese", native_title: "繁體中文", aliases: ["zh_TW"], fallback_code: "en" },
      { code: "zh-HK", title: "Hong Kong Chinese", native_title: "繁體中文香港", aliases: ["zh_HK"], fallback_code: "zh-TW" },
      { code: "ja", title: "Japanese", native_title: "日本語", aliases: ["ja_JP"], fallback_code: "en" },
    ]);

    expect(support.normalizeLanguageCode("zh_CN")).toBe("zh-CN");
    expect(support.normalizeLanguageCode("zh_HK")).toBe("zh-HK");
    expect(support.normalizeLanguageCode("missing")).toBe("en");
    expect(support.getWorkbenchI18nChain("zh-HK")).toEqual(["zh-TW", "en"]);
    expect(support.translate("ja_JP", "title")).toBe("プロンプトワークベンチ");
    expect(support.format("zh_HK", "groupTagInserted", { label: "looking at viewer" })).toBe(
      "已加入 looking at viewer",
    );
  });

  test("formats language option labels and clamps selector placement into viewport", () => {
    expect(formatLanguageOptionLabel({ code: "zh-TW", title: "Traditional Chinese", nativeTitle: "繁體中文" })).toBe(
      "zh-TW - Traditional Chinese (繁體中文)",
    );
    expect(formatLanguageOptionLabel({ code: "en", title: "English", nativeTitle: "English" })).toBe("en - English");

    const placement = computeLanguageSelectorPlacement(
      { left: 900, bottom: 720 },
      { width: 960, height: 760 },
    );

    expect(placement.left).toBeLessThanOrEqual(960 - placement.width - 12);
    expect(placement.top).toBeLessThanOrEqual(760 - placement.maxHeight - 12);
    expect(placement.width).toBeLessThanOrEqual(360);
    expect(placement.maxHeight).toBeGreaterThanOrEqual(120);
  });
});
