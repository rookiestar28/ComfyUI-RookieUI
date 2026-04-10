import {
  describeHostSurface,
  detectHostSurface,
  isHostSurfaceSupported,
} from "../rookieui_host_surface.js";
import { describe, expect, test } from "vitest";

describe("detectHostSurface", () => {
  test("detects desktop by explicit desktop flag", () => {
    expect(detectHostSurface({ __COMFYUI_DESKTOP__: true })).toBe("desktop");
  });

  test("detects desktop by Electron user agent", () => {
    expect(
      detectHostSurface({
        navigator: { userAgent: "Mozilla/5.0 Electron/29.0" },
      }),
    ).toBe("desktop");
  });

  test("detects desktop by electron API bridge", () => {
    expect(detectHostSurface({ electronAPI: {} })).toBe("desktop");
  });

  test("detects standalone web when document is available", () => {
    expect(detectHostSurface({ document: {} })).toBe("standalone-web");
  });

  test("describes the detected host surface", () => {
    expect(describeHostSurface("desktop")).toContain("Desktop");
  });

  test("checks whether the detected surface is supported by capabilities", () => {
    expect(
      isHostSurfaceSupported("desktop", {
        host_surfaces: ["standalone-web", "desktop"],
      }),
    ).toBe(true);
    expect(
      isHostSurfaceSupported("desktop", {
        host_surfaces: ["standalone-web"],
      }),
    ).toBe(false);
  });
});
