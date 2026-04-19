import { describe, expect, test, vi } from "vitest";

import {
  IMG2IMG_GENERATION_MODE_DEFINITIONS,
  createImg2ImgModeRouter,
} from "../sidebar_tabs/rookieui_img2img_mode_router.js";

function createModeInput(value = "img2img") {
  const input = document.createElement("input");
  input.value = value;
  return input;
}

describe("createImg2ImgModeRouter", () => {
  test("activates known subtabs and dispatches mode change", () => {
    const modeInput = createModeInput("img2img");
    const router = createImg2ImgModeRouter({
      modeInput,
      resolveExecutionMode: (mode) => (mode.includes("inpaint") ? "inpaint" : mode),
    });

    const changeSpy = vi.fn();
    modeInput.addEventListener("change", changeSpy);

    const activated = router.activateSubtab("inpaint_upload");
    expect(activated).toBe("inpaint_upload");
    expect(modeInput.value).toBe("inpaint_upload");
    expect(router.getActiveTabId()).toBe("inpaint_upload");
    expect(changeSpy).toHaveBeenCalledTimes(1);
  });

  test("falls back to img2img for unknown mode values", () => {
    const modeInput = createModeInput("unknown_mode");
    const router = createImg2ImgModeRouter({ modeInput });

    const active = router.syncFromModeValue();
    expect(active).toBe("img2img");
    expect(modeInput.value).toBe("img2img");
    expect(router.getActiveTabId()).toBe("img2img");
  });

  test("exposes canonical generation mode definitions", () => {
    const modeInput = createModeInput("img2img");
    const router = createImg2ImgModeRouter({ modeInput });
    expect(router.definitions.map((entry) => entry.id)).toEqual(
      IMG2IMG_GENERATION_MODE_DEFINITIONS.map((entry) => entry.id),
    );
  });

  test("includes edit as a first-class mode", () => {
    const modeInput = createModeInput("edit");
    const router = createImg2ImgModeRouter({ modeInput });

    expect(router.getActiveTabId()).toBe("edit");
    expect(router.definitions.map((entry) => entry.id)).toContain("edit");
  });
});
