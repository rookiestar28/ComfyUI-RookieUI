import { describe, expect, test } from "vitest";

import {
  inspectRookieUIPngInfo as facadeInspectPngInfo,
  parseRookieUIPngInfo,
  submitRookieUIExtras as facadeSubmitExtras,
  submitRookieUIImg2Img as facadeSubmitImg2Img,
  submitRookieUITxt2Img as facadeSubmitTxt2Img,
} from "../rookieui_api.js";
import {
  inspectRookieUIPngInfo,
  submitRookieUIExtras,
  submitRookieUIImg2Img,
  submitRookieUITxt2Img,
} from "../api/rookieui_generation_api.js";
import { postRookieUIJson, toErrorDetail } from "../api/rookieui_api_transport.js";

describe("rookieui API domain exports", () => {
  test("keeps the stable facade wired to generation domain functions", () => {
    expect(facadeSubmitTxt2Img).toBe(submitRookieUITxt2Img);
    expect(facadeSubmitImg2Img).toBe(submitRookieUIImg2Img);
    expect(facadeInspectPngInfo).toBe(inspectRookieUIPngInfo);
    expect(facadeSubmitExtras).toBe(submitRookieUIExtras);
    expect(parseRookieUIPngInfo).toBe(inspectRookieUIPngInfo);
  });

  test("preserves generation no-fetch fallback payloads", async () => {
    await expect(submitRookieUITxt2Img({ prompt: "x" }, null)).resolves.toMatchObject({
      ok: false,
      status: 0,
      data: {
        status: "network-unavailable",
        detail: "RookieUI txt2img submission is unavailable without fetch().",
      },
    });
    await expect(submitRookieUIImg2Img({ prompt: "x" }, null)).resolves.toMatchObject({
      data: { detail: "RookieUI img2img submission is unavailable without fetch()." },
    });
    await expect(inspectRookieUIPngInfo({ image_data: "data:image/png;base64,ZmFrZQ==" }, null)).resolves.toMatchObject({
      data: { detail: "RookieUI pnginfo inspection is unavailable without fetch()." },
    });
    await expect(submitRookieUIExtras({ mode: "single_image" }, null)).resolves.toMatchObject({
      data: { detail: "RookieUI extras submission is unavailable without fetch()." },
    });
  });

  test("shares POST transport success and fallback semantics", async () => {
    const calls = [];
    const result = await postRookieUIJson(
      "/rookieui/example",
      { ok: true },
      { status: "fallback" },
      async (url, options) => {
        calls.push([url, options]);
        return {
          ok: true,
          status: 202,
          async json() {
            return { status: "accepted" };
          },
        };
      },
    );

    expect(result).toEqual({ ok: true, status: 202, data: { status: "accepted" } });
    expect(calls[0][0]).toBe("/rookieui/example");
    expect(JSON.parse(calls[0][1].body)).toEqual({ ok: true });

    await expect(
      postRookieUIJson(
        "/rookieui/example",
        undefined,
        { status: "fallback" },
        async () => {
          throw new Error("offline");
        },
      ),
    ).resolves.toEqual({ ok: false, status: 0, data: { status: "fallback" } });
  });

  test("normalizes API transport error details", () => {
    expect(toErrorDetail(new Error("boom"))).toBe("boom");
    expect(toErrorDetail("plain")).toBe("plain");
    expect(toErrorDetail(null)).toBe("");
  });
});
