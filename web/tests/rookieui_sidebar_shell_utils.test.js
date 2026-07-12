import { describe, expect, test } from "vitest";

import { buildProfileLookup } from "../rookieui_sidebar_shell_utils.js";

describe("sidebar shell profile lookup", () => {
  test("preserves the bounded Ideogram mode contract while merging family metadata", () => {
    const lookup = buildProfileLookup({
      parity: { profiles: [{ id: "ideogram4", title: "Ideogram v4" }] },
      model_families: {
        entries: [
          {
            id: "ideogram4",
            title: "Ideogram v4",
            translation_base_family: "sdxl",
            public_base_family: "ideogram4",
            ideogram_modes: ["quality", "default", "turbo"],
            default_ideogram_mode: "default",
          },
        ],
      },
    });

    expect(lookup.get("ideogram4")).toMatchObject({
      ideogram_modes: ["quality", "default", "turbo"],
      default_ideogram_mode: "default",
    });
  });

  test("preserves template LoRA activation defaults independently from selector availability", () => {
    const lookup = buildProfileLookup({
      parity: { profiles: [{ id: "krea2_turbo", title: "Krea-2 Turbo" }] },
      model_families: {
        entries: [
          {
            id: "krea2_turbo",
            title: "Krea-2 Turbo",
            template_lora_visible: true,
            default_template_lora_enabled: false,
            default_template_lora_strength: 0.8,
            default_template_lora_trigger_word: "muted minimalist sketch style",
            template_lora_trigger_visible: true,
          },
        ],
      },
    });

    expect(lookup.get("krea2_turbo")).toMatchObject({
      default_template_lora_enabled: false,
      default_template_lora_strength: 0.8,
      default_template_lora_trigger_word: "muted minimalist sketch style",
      template_lora_trigger_visible: true,
    });
  });
});
