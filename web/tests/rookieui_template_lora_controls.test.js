import { describe, expect, test } from "vitest";

import { createTemplateLoraController } from "../sidebar_tabs/rookieui_template_lora_controls.js";

const input = (value = "") => ({ value, disabled: false });
const checkbox = (checked = false) => ({ checked, disabled: false });

describe("template LoRA controls", () => {
  test("keeps installed Krea selector inactive until explicitly enabled", () => {
    const elements = {
      preset: input("krea2_turbo"),
      profileState: input("krea2_turbo"),
      templateLoraName: input("Krea/krea2_darkbrush.safetensors"),
      templateLoraEnabled: checkbox(true),
      templateLoraStrength: input("1"),
      templateLoraTriggerWord: input("stale trigger"),
      steps: input("99"),
      stepsSlider: input("99"),
    };
    const controls = {
      field: null,
      enableField: null,
      strengthField: null,
      triggerField: null,
      statusNode: null,
      resetButton: null,
      libraryHeading: null,
      libraryHost: null,
    };
    const profileLookup = new Map([
      [
        "krea2_turbo",
        {
          id: "krea2_turbo",
          template_lora_visible: true,
          template_lora_override_allowed: true,
          default_template_lora_enabled: false,
          default_template_lora_strength: 0.8,
          default_template_lora_trigger_word: "muted minimalist sketch style",
          template_lora_trigger_visible: true,
        },
      ],
    ]);
    const presetLookup = new Map([
      ["krea2_turbo", { template_lora_name: "Krea/krea2_darkbrush.safetensors" }],
    ]);
    const controller = createTemplateLoraController({
      profileLookup,
      presetLookup,
      elements,
      controls,
      setElementValue(element, value) {
        if ("checked" in element) {
          element.checked = Boolean(value);
        } else {
          element.value = String(value);
        }
      },
    });

    controller.sync({ resetDefaults: true });
    expect(elements.templateLoraName.value).toBe("Krea/krea2_darkbrush.safetensors");
    expect(elements.templateLoraEnabled.checked).toBe(false);
    expect(elements.templateLoraStrength.value).toBe("0.8");
    expect(elements.templateLoraTriggerWord.value).toBe("muted minimalist sketch style");

    elements.templateLoraEnabled.checked = true;
    controller.sync();
    expect(elements.templateLoraStrength.disabled).toBe(false);
    expect(elements.templateLoraTriggerWord.disabled).toBe(false);
  });

  test("couples Flux.2 activation UI to source-backed 20 and 8 steps", () => {
    const elements = {
      preset: input("flux2_dev"),
      profileState: input("flux2_dev"),
      templateLoraName: input("Flux/Flux_2-Turbo-LoRA_comfyui.safetensors"),
      templateLoraEnabled: checkbox(false),
      templateLoraStrength: input("1"),
      templateLoraTriggerWord: input(""),
      steps: input("20"),
      stepsSlider: input("20"),
    };
    const profileLookup = new Map([
      [
        "flux2_dev",
        {
          id: "flux2_dev",
          template_lora_visible: true,
          template_lora_override_allowed: true,
          default_template_lora_enabled: false,
          default_template_lora_strength: 1,
          default_template_lora_trigger_word: "",
          template_lora_trigger_visible: false,
        },
      ],
    ]);
    const controller = createTemplateLoraController({
      profileLookup,
      presetLookup: new Map(),
      elements,
      controls: {},
      setElementValue(element, value) {
        if ("checked" in element) {
          element.checked = Boolean(value);
        } else {
          element.value = String(value);
        }
      },
    });

    controller.sync();
    expect(elements.steps.value).toBe("20");
    elements.templateLoraEnabled.checked = true;
    controller.sync();
    expect(elements.steps.value).toBe("8");
    expect(elements.stepsSlider.value).toBe("8");
  });
});
