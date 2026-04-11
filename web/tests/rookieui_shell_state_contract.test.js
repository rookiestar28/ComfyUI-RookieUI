import { describe, expect, test, vi } from "vitest";

import { createShellStateEventContract } from "../sidebar_tabs/rookieui_shell_state_contract.js";

describe("createShellStateEventContract", () => {
  test("tracks active top tab through controller activation callbacks", () => {
    const formRegistry = {};
    const contract = createShellStateEventContract(formRegistry);
    const activateTabById = vi.fn();

    contract.registerTopTabController({ activateTabById });
    expect(contract.activateTopTab("img2img")).toBe(true);
    expect(activateTabById).toHaveBeenCalledWith("img2img");
    expect(contract.getActiveTopTab()).toBe("img2img");
  });

  test("registers pane state locks on shared registry bridge", () => {
    const formRegistry = {};
    const contract = createShellStateEventContract(formRegistry);
    const lock = {
      capture: vi.fn(),
      restore: vi.fn(),
    };

    contract.registerPaneStateLock("txt2img", lock);
    const registered = contract.getPaneStateLock("txt2img");
    expect(registered).not.toBeNull();
    registered.capture();
    registered.restore();
    expect(lock.capture).toHaveBeenCalledTimes(1);
    expect(lock.restore).toHaveBeenCalledTimes(1);
    expect(formRegistry.__paneStateLocks.txt2img).toBe(registered);
  });

  test("dispatches cross-pane payload apply with optional activation", () => {
    const applyPayload = vi.fn();
    const activateTabById = vi.fn();
    const formRegistry = {
      img2img: { applyPayload },
    };
    const contract = createShellStateEventContract(formRegistry);
    contract.registerTopTabController({ activateTabById });

    const payload = { image_asset: "asset-1", mode: "img2img" };
    expect(contract.applyToForm("img2img", payload)).toBe(true);
    expect(activateTabById).toHaveBeenCalledWith("img2img");
    expect(applyPayload).toHaveBeenCalledWith(payload);

    activateTabById.mockClear();
    expect(contract.applyToForm("img2img", payload, { activate: false })).toBe(true);
    expect(activateTabById).not.toHaveBeenCalled();
    expect(contract.applyToForm("txt2img", payload)).toBe(false);
  });
});
