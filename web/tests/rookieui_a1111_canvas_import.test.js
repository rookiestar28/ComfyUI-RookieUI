import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { createDefaultCapabilities } from "../rookieui_api.js";
import { registerRookieUIBootstrapExtension } from "../rookieui_extension.js";

function buildPngTextFile(metadataItems) {
  const encoder = new TextEncoder();
  const chunks = [];
  const signature = Uint8Array.from([137, 80, 78, 71, 13, 10, 26, 10]);

  function chunk(type, data) {
    const typeBytes = encoder.encode(type);
    const lengthBytes = new Uint8Array(4);
    new DataView(lengthBytes.buffer).setUint32(0, data.length);
    chunks.push(lengthBytes, typeBytes, data, Uint8Array.from([0, 0, 0, 0]));
  }

  const ihdr = new Uint8Array(13);
  new DataView(ihdr.buffer).setUint32(0, 32);
  new DataView(ihdr.buffer).setUint32(4, 32);
  ihdr[8] = 8;
  ihdr[9] = 2;
  chunk("IHDR", ihdr);
  for (const [key, value] of Object.entries(metadataItems)) {
    const keyBytes = encoder.encode(key);
    const valueBytes = encoder.encode(value);
    const data = new Uint8Array(keyBytes.length + 1 + valueBytes.length);
    data.set(keyBytes, 0);
    data[keyBytes.length] = 0;
    data.set(valueBytes, keyBytes.length + 1);
    chunk("tEXt", data);
  }
  chunk("IEND", new Uint8Array(0));

  const bytes = new Uint8Array([signature, ...chunks].reduce((total, part) => total + part.length, 0));
  let offset = 0;
  for (const part of [signature, ...chunks]) {
    bytes.set(part, offset);
    offset += part.length;
  }
  return new File([bytes], "a1111.png", { type: "image/png" });
}

function createMockNode(type, { text = "" } = {}) {
  return {
    id: null,
    type,
    comfyClass: type,
    title: type,
    pos: [0, 0],
    size: [300, 160],
    widgets: text ? [{ name: "text", value: text }] : [],
    inputs: [{ name: "clip", link: null }],
    outputs: [{ name: "CONDITIONING", links: [] }],
    connect(outputIndex, targetNode, targetSlot) {
      const graph = this.graph;
      if (!graph) {
        throw new Error("node must be added to graph before connecting");
      }
      const linkId = graph.nextLinkId++;
      graph.links[linkId] = {
        id: linkId,
        origin_id: this.id,
        origin_slot: outputIndex,
        target_id: targetNode.id,
        target_slot: targetSlot,
      };
      this.outputs[outputIndex].links.push(linkId);
      targetNode.inputs[targetSlot].link = linkId;
    },
  };
}

function createMockGraph() {
  return {
    _nodes: [],
    links: {},
    nextNodeId: 1,
    nextLinkId: 1,
    add(node) {
      node.id ||= this.nextNodeId++;
      node.graph = this;
      this._nodes.push(node);
    },
    clear() {
      this._nodes = [];
      this.links = {};
    },
    getNodeById(id) {
      return this._nodes.find((node) => String(node.id) === String(id)) ?? null;
    },
    remove(nodeToRemove) {
      const linkIds = new Set();
      for (const input of nodeToRemove.inputs ?? []) {
        if (input.link != null) {
          linkIds.add(input.link);
        }
      }
      for (const output of nodeToRemove.outputs ?? []) {
        for (const linkId of output.links ?? []) {
          linkIds.add(linkId);
        }
      }
      for (const linkId of linkIds) {
        const link = this.links[linkId];
        if (!link) continue;
        const origin = this.getNodeById(link.origin_id);
        const target = this.getNodeById(link.target_id);
        const originLinks = origin?.outputs?.[link.origin_slot]?.links;
        if (Array.isArray(originLinks)) {
          origin.outputs[link.origin_slot].links = originLinks.filter((id) => id !== linkId);
        }
        if (target?.inputs?.[link.target_slot]) {
          target.inputs[link.target_slot].link = null;
        }
        delete this.links[linkId];
      }
      this._nodes = this._nodes.filter((node) => node !== nodeToRemove);
    },
    setDirtyCanvas: vi.fn(),
  };
}

function createNativeA1111ImportGraph(graph) {
  graph.clear();
  const clip = createMockNode("CLIPSetLastLayer");
  clip.outputs = [{ name: "CLIP", links: [] }];
  const positive = createMockNode("CLIPTextEncode", { text: "canvas positive prompt" });
  const negative = createMockNode("CLIPTextEncode", { text: "canvas negative prompt" });
  const sampler = createMockNode("KSampler");
  sampler.inputs = [{ name: "model", link: null }, { name: "positive", link: null }, { name: "negative", link: null }];
  graph.add(clip);
  graph.add(positive);
  graph.add(negative);
  graph.add(sampler);
  clip.connect(0, positive, 0);
  clip.connect(0, negative, 0);
  positive.connect(0, sampler, 1);
  negative.connect(0, sampler, 2);
}

describe("A1111 PNG direct canvas import encoder routing", () => {
  let originalLiteGraph;

  beforeEach(() => {
    document.body.innerHTML = "";
    document.head.innerHTML = "";
    delete window.__ROOKIEUI_BOOTSTRAP__;
    originalLiteGraph = window.LiteGraph;
    window.LiteGraph = {
      createNode(type) {
        const node = createMockNode(type);
        node.widgets = [
          { name: "width", value: 1024 },
          { name: "height", value: 1024 },
          { name: "crop_w", value: 0 },
          { name: "crop_h", value: 0 },
          { name: "target_width", value: 1024 },
          { name: "target_height", value: 1024 },
          { name: "text_g", value: "" },
          { name: "text_l", value: "" },
          { name: "steps", value: 10 },
        ];
        return node;
      },
    };
  });

  afterEach(() => {
    window.LiteGraph = originalLiteGraph;
  });

  test("rewrites A1111 PNG fallback imports from native CLIPTextEncode to RookieUI SDXL parity encoders", async () => {
    const graph = createMockGraph();
    const originalHandleFile = vi.fn(async () => {
      createNativeA1111ImportGraph(graph);
    });
    const app = {
      rootGraph: graph,
      canvas: { setDirty: vi.fn(), setDirtyCanvas: vi.fn() },
      handleFile: originalHandleFile,
      registerExtension(definition) {
        return Promise.resolve(definition.setup());
      },
      api: {
        clientId: "canvas-import-test-client",
        addEventListener() {},
        removeEventListener() {},
      },
      extensionManager: {
        registerSidebarTab() {},
      },
    };
    const fetchImpl = vi.fn(async (url) => {
      if (url === "/rookieui/capabilities") {
        return {
          ok: true,
          status: 200,
          async json() {
            return createDefaultCapabilities();
          },
        };
      }
      if (url === "/rookieui/pnginfo/inspect") {
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              status: "ok",
              source_type: "a1111",
              target_form: "txt2img",
              payload: {
                profile: "sdxl",
                prompt: "canvas positive prompt",
                negative_prompt: "canvas negative prompt",
                width: 832,
                height: 1216,
                steps: 20,
              },
            };
          },
        };
      }
      return {
        ok: false,
        status: 404,
        async json() {
          return {};
        },
      };
    });

    await registerRookieUIBootstrapExtension({ app, fetchImpl });
    expect(app.__rookieuiA1111CanvasImportParityPatch).toBe(true);
    const file = buildPngTextFile({
      parameters: [
        "canvas positive prompt",
        "Negative prompt: canvas negative prompt",
        "Steps: 20, Sampler: Euler a, CFG scale: 7, Seed: 3322577650, Size: 832x1216, Model: hassakuWIPV3, VAE: sdxl_vaeFix.safetensors, Denoising strength: 0.38, Hires upscale: 1.3",
      ].join("\n"),
    });

    await app.handleFile(file);

    const classTypes = graph._nodes.map((node) => node.comfyClass);
    expect(fetchImpl).toHaveBeenCalledWith("/rookieui/pnginfo/inspect", expect.any(Object));
    expect(originalHandleFile).toHaveBeenCalledTimes(1);
    expect(originalHandleFile.mock.calls[0][0]).toBe(file);
    expect(classTypes).not.toContain("CLIPTextEncode");
    expect(classTypes.filter((classType) => classType === "RookieUIA1111CLIPTextEncodeSDXL")).toHaveLength(2);

    const rookieNodes = graph._nodes.filter((node) => node.comfyClass === "RookieUIA1111CLIPTextEncodeSDXL");
    expect(rookieNodes.map((node) => node.widgets.find((widget) => widget.name === "text_g")?.value)).toEqual([
      "canvas positive prompt",
      "canvas negative prompt",
    ]);
    expect(rookieNodes[0].widgets.find((widget) => widget.name === "width")?.value).toBe(832);
    expect(rookieNodes[0].widgets.find((widget) => widget.name === "height")?.value).toBe(1216);
    expect(rookieNodes[0].outputs[0].links).toHaveLength(1);
  });

  test("does not rewrite images that already carry ComfyUI workflow metadata", async () => {
    const graph = createMockGraph();
    const app = {
      rootGraph: graph,
      canvas: { setDirty: vi.fn(), setDirtyCanvas: vi.fn() },
      handleFile: vi.fn(async () => {
        createNativeA1111ImportGraph(graph);
      }),
      registerExtension(definition) {
        return Promise.resolve(definition.setup());
      },
      api: {
        clientId: "canvas-import-workflow-skip-client",
        addEventListener() {},
        removeEventListener() {},
      },
      extensionManager: {
        registerSidebarTab() {},
      },
    };
    const fetchImpl = vi.fn(async (url) => ({
      ok: url === "/rookieui/capabilities",
      status: url === "/rookieui/capabilities" ? 200 : 404,
      async json() {
        return url === "/rookieui/capabilities" ? createDefaultCapabilities() : {};
      },
    }));

    await registerRookieUIBootstrapExtension({ app, fetchImpl });
    const file = buildPngTextFile({
      workflow: JSON.stringify({ nodes: [] }),
      parameters: "positive\nNegative prompt: negative\nSteps: 20, Sampler: Euler a",
    });

    await app.handleFile(file);

    expect(fetchImpl.mock.calls.some(([url]) => url === "/rookieui/pnginfo/inspect")).toBe(false);
    expect(graph._nodes.map((node) => node.comfyClass)).toContain("CLIPTextEncode");
  });

  test("uses backend PNG inspection when local metadata extraction cannot see A1111 parameters", async () => {
    const graph = createMockGraph();
    const originalHandleFile = vi.fn(async () => {
      createNativeA1111ImportGraph(graph);
    });
    const app = {
      rootGraph: graph,
      canvas: { setDirty: vi.fn(), setDirtyCanvas: vi.fn() },
      handleFile: originalHandleFile,
      registerExtension(definition) {
        return Promise.resolve(definition.setup());
      },
      api: {
        clientId: "canvas-import-backend-only-client",
        addEventListener() {},
        removeEventListener() {},
      },
      extensionManager: {
        registerSidebarTab() {},
      },
    };
    const fetchImpl = vi.fn(async (url) => {
      if (url === "/rookieui/capabilities") {
        return {
          ok: true,
          status: 200,
          async json() {
            return createDefaultCapabilities();
          },
        };
      }
      if (url === "/rookieui/pnginfo/inspect") {
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              status: "ok",
              source_type: "a1111",
              target_form: "txt2img",
              payload: {
                profile: "sdxl",
                prompt: "backend positive prompt",
                negative_prompt: "backend negative prompt",
                width: 832,
                height: 1216,
                steps: 20,
              },
            };
          },
        };
      }
      return {
        ok: false,
        status: 404,
        async json() {
          return {};
        },
      };
    });

    await registerRookieUIBootstrapExtension({ app, fetchImpl });
    const file = buildPngTextFile({});

    await app.handleFile(file);

    expect(fetchImpl).toHaveBeenCalledWith("/rookieui/pnginfo/inspect", expect.any(Object));
    expect(graph._nodes.map((node) => node.comfyClass)).not.toContain("CLIPTextEncode");
    expect(graph._nodes.filter((node) => node.comfyClass === "RookieUIA1111CLIPTextEncodeSDXL")).toHaveLength(2);
  });
});
