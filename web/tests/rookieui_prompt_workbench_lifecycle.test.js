import { afterEach, describe, expect, test, vi } from "vitest";

import { createPromptWorkbenchLifecycle } from "../sidebar_tabs/prompt_workbench/rookieui_prompt_workbench_lifecycle.js";

describe("Prompt Workbench lifecycle ownership", () => {
  afterEach(() => {
    vi.useRealTimers();
    document.body.replaceChildren();
  });

  test("tracks timers, external listeners, child disposers, and abort controllers idempotently", () => {
    vi.useFakeTimers();
    const lifecycle = createPromptWorkbenchLifecycle();
    const target = new EventTarget();
    const handler = vi.fn();
    const childDestroy = vi.fn();
    const abortController = new AbortController();
    lifecycle.listen(target, "change", handler);
    lifecycle.timeout(handler, 100);
    lifecycle.own(childDestroy);
    lifecycle.trackAbortController(abortController);

    target.dispatchEvent(new Event("change"));
    expect(handler).toHaveBeenCalledTimes(1);
    lifecycle.destroy();
    lifecycle.destroy();
    vi.advanceTimersByTime(200);
    target.dispatchEvent(new Event("change"));

    expect(handler).toHaveBeenCalledTimes(1);
    expect(childDestroy).toHaveBeenCalledTimes(1);
    expect(abortController.signal.aborted).toBe(true);
    expect(lifecycle.destroyed).toBe(true);
  });

  test("removes feature-owned overlays while preserving shared prompt inputs", () => {
    const lifecycle = createPromptWorkbenchLifecycle();
    const input = document.createElement("textarea");
    const overlay = document.createElement("div");
    document.body.append(input, overlay);
    lifecycle.trackNode(overlay);
    lifecycle.destroy();

    expect(input.isConnected).toBe(true);
    expect(overlay.isConnected).toBe(false);
  });

  test("cancels replaced timers without retaining them until destroy", () => {
    vi.useFakeTimers();
    const lifecycle = createPromptWorkbenchLifecycle();
    const handler = vi.fn();
    const timer = lifecycle.timeout(handler, 100);
    lifecycle.cancel(timer);
    vi.advanceTimersByTime(200);

    expect(handler).not.toHaveBeenCalled();
  });
});
