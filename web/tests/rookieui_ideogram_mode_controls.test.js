import { describe, expect, test } from "vitest";

import {
  createIdeogramModeController,
  createIdeogramModeSelect,
} from "../sidebar_tabs/rookieui_ideogram_mode_controls.js";

function createSelect(id, options, selectedValue) {
  const select = document.createElement("select");
  select.id = id;
  options.forEach(({ value, label }) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    select.appendChild(option);
  });
  select.value = selectedValue;
  return select;
}

describe("Ideogram mode controls", () => {
  test("hide for generic profiles and expose only source-backed modes for Ideogram", () => {
    const input = createIdeogramModeSelect(createSelect);
    const profileInput = { value: "sd15" };
    const profileLookup = new Map([
      ["sd15", { id: "sd15", ideogram_modes: [], default_ideogram_mode: "" }],
      [
        "ideogram4",
        {
          id: "ideogram4",
          ideogram_modes: ["quality", "default", "turbo"],
          default_ideogram_mode: "default",
        },
      ],
    ]);
    const field = document.createElement("label");
    field.appendChild(input);
    const controller = createIdeogramModeController(
      input,
      profileInput,
      profileLookup,
      (element, value) => {
        element.value = value;
      },
    );

    controller.attach(field);
    expect(field.hidden).toBe(true);
    expect(input.disabled).toBe(true);

    profileInput.value = "ideogram4";
    input.value = "";
    controller.sync();
    expect(field.hidden).toBe(false);
    expect(input.disabled).toBe(false);
    expect(input.value).toBe("default");
    expect(Array.from(input.options, (option) => option.value)).toEqual(["quality", "default", "turbo"]);

    input.value = "turbo";
    controller.sync();
    expect(input.value).toBe("turbo");
  });
});
