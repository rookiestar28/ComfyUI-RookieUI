import { afterEach, describe, expect, test, vi } from "vitest";

import { postRookieUIJson } from "../../web/api/rookieui_api_transport.js";


describe("candidate host POST outcome contract", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  test.each([
    ["TimeoutError", "timeout"],
    ["AbortError", "cancelled"],
    ["TypeError", "network-unknown"],
  ])("preserves %s as %s rather than a definite rejection", async (name, failureKind) => {
    const result = await postRookieUIJson(
      "/rookieui/generate/txt2img",
      { prompt: "private prompt" },
      { status: "network-unavailable" },
      async () => { throw new DOMException("transport stopped", name); },
    );
    expect(result).toMatchObject({ ok: false, status: 0, failure_kind: failureKind, request_outcome: "unknown" });
  });

  test("HTTP rejection is distinct from an accepted response with invalid JSON", async () => {
    const rejected = await postRookieUIJson("/rookieui/generate/txt2img", {}, {}, async () => ({
      ok: false, status: 409, json: async () => ({ status: "rejected" }),
    }));
    expect(rejected).toMatchObject({ ok: false, status: 409, failure_kind: "http", request_outcome: "rejected" });

    const invalid = await postRookieUIJson("/rookieui/generate/txt2img", {}, {}, async () => ({
      ok: true, status: 202, json: async () => { throw new SyntaxError("invalid JSON"); },
    }));
    expect(invalid).toMatchObject({ ok: false, status: 202, failure_kind: "invalid-response", request_outcome: "unknown" });
  });

  test("forwards caller cancellation and finite 60-second host deadline", async () => {
    const controller = new AbortController();
    let seen;
    const fetchImpl = vi.fn(async (_path, options) => {
      seen = options;
      return { ok: true, status: 202, json: async () => ({ status: "queued" }) };
    });
    await postRookieUIJson("/rookieui/generate/txt2img", {}, {}, fetchImpl, { signal: controller.signal });
    expect(seen.timeoutMs).toBe(60_000);
    expect(seen.signal).toBeInstanceOf(AbortSignal);
    expect(seen.signal.aborted).toBe(false);

    controller.abort();
    const noFetch = vi.fn();
    const result = await postRookieUIJson("/rookieui/generate/txt2img", {}, {}, noFetch, { signal: controller.signal });
    expect(noFetch).not.toHaveBeenCalled();
    expect(result).toMatchObject({ failure_kind: "cancelled", request_outcome: "not-sent" });
  });

  test("enforces the same deadline for plain fetch without retrying an uncertain POST", async () => {
    vi.useFakeTimers();
    const fetchImpl = vi.fn((_path, { signal }) => new Promise((_resolve, reject) => {
      signal.addEventListener("abort", () => reject(signal.reason), { once: true });
    }));
    const pending = postRookieUIJson("/rookieui/generate/txt2img", {}, {}, fetchImpl, { timeoutMs: 20 });
    await vi.advanceTimersByTimeAsync(20);
    await expect(pending).resolves.toMatchObject({ failure_kind: "timeout", request_outcome: "unknown" });
    expect(fetchImpl).toHaveBeenCalledTimes(1);
    expect(vi.getTimerCount()).toBe(0);
  });

  test("keeps caller cancellation distinct while an accepted response body is pending", async () => {
    const caller = new AbortController();
    const pending = postRookieUIJson("/rookieui/generate/txt2img", {}, {}, async (_path, { signal }) => ({
      ok: true,
      status: 202,
      json: () => new Promise((_resolve, reject) => {
        signal.addEventListener("abort", () => reject(signal.reason), { once: true });
      }),
    }), { signal: caller.signal });
    await Promise.resolve();
    caller.abort();
    await expect(pending).resolves.toMatchObject({
      ok: false,
      status: 202,
      failure_kind: "cancelled",
      request_outcome: "unknown",
    });
  });
});
