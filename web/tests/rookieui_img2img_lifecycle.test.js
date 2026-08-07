import { afterEach, describe, expect, test, vi } from "vitest";

import { createImg2ImgLifecycle } from "../sidebar_tabs/img2img/rookieui_img2img_lifecycle.js";

describe("createImg2ImgLifecycle", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  test("owns listeners, timers, objects, nodes, aborts, and child controllers exactly once", () => {
    const lifecycle = createImg2ImgLifecycle();
    const target = new EventTarget();
    const handler = vi.fn();
    const child = { destroy: vi.fn() };
    const node = document.createElement("div");
    document.body.appendChild(node);
    const abort = new AbortController();
    const revoke = vi.fn();

    lifecycle.listen(target, "change", handler);
    lifecycle.trackAbortController(abort);
    lifecycle.trackObjectUrl("blob:f310", revoke);
    lifecycle.trackNode(node);
    lifecycle.own(child);

    target.dispatchEvent(new Event("change"));
    expect(handler).toHaveBeenCalledTimes(1);
    lifecycle.destroy();
    lifecycle.destroy();
    target.dispatchEvent(new Event("change"));

    expect(handler).toHaveBeenCalledTimes(1);
    expect(abort.signal.aborted).toBe(true);
    expect(revoke).toHaveBeenCalledTimes(1);
    expect(child.destroy).toHaveBeenCalledTimes(1);
    expect(node.isConnected).toBe(false);
    expect(lifecycle.destroyed).toBe(true);
  });

  test("cancels pending timers and rejects late callbacks after destroy", async () => {
    const lifecycle = createImg2ImgLifecycle();
    const callback = vi.fn();
    lifecycle.timeout(callback, 0);
    lifecycle.destroy();
    await new Promise((resolve) => setTimeout(resolve, 5));
    expect(callback).not.toHaveBeenCalled();
  });
});
