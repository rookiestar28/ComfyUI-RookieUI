import { afterEach, describe, expect, test, vi } from "vitest";

import {
  createGenerationRuntimeHelpers,
  createGenerationRuntimeState,
} from "../../web/rookieui_generation_runtime.js";

const RGBA_PNG = "iVBORw0KGgoAAAANSUhEUgAAAAIAAAABCAYAAAD0In+KAAAAEUlEQVR4nGNkZGJmYGZmbgAAANUAkaVBWMMAAAAASUVORK5CYII=";

function makeSubject(fetchImpl) {
  vi.stubGlobal("fetch", fetchImpl);
  const applyCrossPanePayload = vi.fn(() => true);
  const helpers = createGenerationRuntimeHelpers({
    emitFrontendDebugWarning: vi.fn(),
    setPreviewContent: vi.fn(),
    applyCrossPanePayload,
    activateShellTab: vi.fn(),
  });
  const runtimeState = createGenerationRuntimeState();
  runtimeState.finalImageUrl = "/view?filename=final-rgba.png&type=output";
  runtimeState.finalImageDescriptor = { filename: "final-rgba.png", type: "output", selectedIndex: 0 };
  const previewBox = document.createElement("div");
  previewBox.innerHTML = '<img src="data:image/png;base64,c3RhbGU=" alt="stale preview">';
  const statusNode = document.createElement("p");
  return { helpers, runtimeState, previewBox, statusNode, applyCrossPanePayload };
}

describe("RGBA original-output transfer", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  test("PNG Info and edit receive identical original RGBA PNG bytes, never stale preview bytes", async () => {
    const bytes = Uint8Array.from(atob(RGBA_PNG), (character) => character.charCodeAt(0));
    const fetchImpl = vi.fn(async () => ({
      ok: true,
      status: 200,
      blob: async () => new Blob([bytes], { type: "image/png" }),
    }));
    const subject = makeSubject(fetchImpl);
    const registry = { img2img: { applyPayload: vi.fn() } };

    await subject.helpers.transferPreviewToPngInfo(registry, subject.runtimeState, subject.statusNode, subject.previewBox);
    await subject.helpers.transferPreviewToImg2Img(registry, subject.runtimeState, subject.statusNode, subject.previewBox, {
      requireOriginalImageData: true,
    });

    expect(fetchImpl).toHaveBeenCalledTimes(2);
    expect(fetchImpl).toHaveBeenCalledWith("/view?filename=final-rgba.png&type=output");
    const calls = subject.applyCrossPanePayload.mock.calls;
    expect(calls.map(([, pane]) => pane)).toEqual(["pnginfo", "img2img"]);
    for (const [, , payload] of calls) {
      expect(payload.image_data).toBe(`data:image/png;base64,${RGBA_PNG}`);
      expect(payload.image_asset).toBe("");
    }
  });

  test("alpha-safe edit transfer refuses a failed original fetch instead of claiming a fallback succeeded", async () => {
    const subject = makeSubject(vi.fn(async () => { throw new Error("synthetic fetch failure"); }));
    const registry = { img2img: { applyPayload: vi.fn() } };

    await subject.helpers.transferPreviewToImg2Img(registry, subject.runtimeState, subject.statusNode, subject.previewBox, {
      requireOriginalImageData: true,
    });

    expect(subject.applyCrossPanePayload).not.toHaveBeenCalled();
    expect(subject.statusNode.textContent).toMatch(/Original PNG is unavailable/);
  });
});
