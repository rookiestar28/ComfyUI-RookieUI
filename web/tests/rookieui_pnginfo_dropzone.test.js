import { describe, expect, test, vi } from "vitest";

import { buildPngInfoPane } from "../sidebar_tabs/rookieui_pnginfo_pane.js";

function createContext() {
  return {
    appendTextElement(parent, tagName, className, text) {
      const element = document.createElement(tagName);
      element.className = className;
      element.textContent = text;
      parent.appendChild(element);
      return element;
    },
    createInput(type, id, value, options = {}) {
      const element = document.createElement("input");
      element.type = type;
      element.id = id;
      element.value = value;
      if (options.className) {
        element.className = options.className;
      }
      return element;
    },
    createActionButton(id, label) {
      const button = document.createElement("button");
      button.type = "button";
      button.id = id;
      button.textContent = label;
      return button;
    },
    createMiniActionButton(id, label) {
      const button = document.createElement("button");
      button.type = "button";
      button.id = id;
      button.textContent = label;
      return button;
    },
    createList(id) {
      const list = document.createElement("ul");
      list.id = id;
      return list;
    },
    setPreviewContent: vi.fn(),
    setPngInfoSummaryVisibility: vi.fn(),
    setListVisibility: vi.fn(),
    updatePngInfoApplyButtons: vi.fn(),
    inspectPngInfo: vi.fn(async () => {}),
    writeTextToClipboard: vi.fn(async () => true),
    applyPngInfoResult: vi.fn(),
    readFileAsDataUrl: vi.fn(async () => "data:image/png;base64,ZmFrZQ=="),
    emitFrontendDebugWarning: vi.fn(),
  };
}

describe("PNG Info dropzone event containment", () => {
  test("stops image drop events before they reach host canvas import listeners", () => {
    document.body.innerHTML = "";
    const hostDropListener = vi.fn();
    const parent = document.createElement("div");
    parent.addEventListener("drop", hostDropListener);
    document.body.appendChild(parent);

    buildPngInfoPane(parent, {}, {}, createContext());
    const dropzone = document.getElementById("rookieui-pnginfo-dropzone");
    const file = new File([Uint8Array.from([137, 80, 78, 71])], "a1111.png", { type: "image/png" });
    const event = new Event("drop", { bubbles: true, cancelable: true });
    Object.defineProperty(event, "dataTransfer", {
      value: { files: [file] },
    });

    dropzone.dispatchEvent(event);

    expect(event.defaultPrevented).toBe(true);
    expect(hostDropListener).not.toHaveBeenCalled();
  });
});
