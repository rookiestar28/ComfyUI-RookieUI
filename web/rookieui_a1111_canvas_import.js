const PNG_SIGNATURE = [137, 80, 78, 71, 13, 10, 26, 10];
const SDXL_PROFILES = new Set(["sdxl", "pony", "illustrious", "noob"]);

function isPngBuffer(bytes) {
  return PNG_SIGNATURE.every((value, index) => bytes[index] === value);
}

function decodeText(bytes) {
  return new TextDecoder("utf-8").decode(bytes);
}

function readUint32(bytes, offset) {
  return new DataView(bytes.buffer, bytes.byteOffset + offset, 4).getUint32(0);
}

function findNullByte(bytes, startIndex = 0) {
  for (let index = startIndex; index < bytes.length; index += 1) {
    if (bytes[index] === 0) {
      return index;
    }
  }
  return -1;
}

function readTextChunk(type, data) {
  const keyEnd = findNullByte(data);
  if (keyEnd <= 0) {
    return null;
  }
  const key = decodeText(data.slice(0, keyEnd));
  if (!key) {
    return null;
  }
  if (type === "tEXt") {
    return [key, decodeText(data.slice(keyEnd + 1))];
  }
  if (type !== "iTXt") {
    return null;
  }

  const compressionFlag = data[keyEnd + 1];
  if (compressionFlag !== 0) {
    return null;
  }
  const languageEnd = findNullByte(data, keyEnd + 3);
  if (languageEnd < 0) {
    return null;
  }
  const translatedKeywordEnd = findNullByte(data, languageEnd + 1);
  if (translatedKeywordEnd < 0) {
    return null;
  }
  return [key, decodeText(data.slice(translatedKeywordEnd + 1))];
}

export function extractPngTextMetadataFromArrayBuffer(buffer) {
  const bytes = new Uint8Array(buffer);
  const metadata = {};
  if (bytes.length < 12 || !isPngBuffer(bytes)) {
    return metadata;
  }

  let offset = 8;
  while (offset + 12 <= bytes.length) {
    const length = readUint32(bytes, offset);
    const type = decodeText(bytes.slice(offset + 4, offset + 8));
    const dataStart = offset + 8;
    const dataEnd = dataStart + length;
    if (dataEnd + 4 > bytes.length) {
      break;
    }
    if (type === "tEXt" || type === "iTXt") {
      const entry = readTextChunk(type, bytes.slice(dataStart, dataEnd));
      if (entry) {
        const [key, value] = entry;
        metadata[key] = value;
      }
    }
    offset = dataEnd + 4;
    if (type === "IEND") {
      break;
    }
  }
  return metadata;
}

function hasEmbeddedComfyWorkflow(metadata) {
  return typeof metadata.workflow === "string" || typeof metadata.prompt === "string";
}

function isLikelyA1111Parameters(parameters) {
  return typeof parameters === "string" && /\nSteps:\s*\d+/i.test(parameters) && /,\s*Sampler:/i.test(parameters);
}

function arrayBufferToDataUrl(buffer, mimeType) {
  if (typeof btoa !== "function") {
    return "";
  }
  const bytes = new Uint8Array(buffer);
  let binary = "";
  const chunkSize = 0x8000;
  for (let offset = 0; offset < bytes.length; offset += chunkSize) {
    binary += String.fromCharCode(...bytes.slice(offset, offset + chunkSize));
  }
  return `data:${mimeType || "image/png"};base64,${btoa(binary)}`;
}

function canReadFileBuffer(file) {
  return typeof file?.arrayBuffer === "function" || typeof FileReader !== "undefined";
}

async function readFileBuffer(file) {
  if (typeof file?.arrayBuffer === "function") {
    return file.arrayBuffer();
  }
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error || new Error("Failed to read PNG file metadata."));
    reader.readAsArrayBuffer(file);
  });
}

function isLikelyPngFile(file) {
  const type = String(file?.type || "").toLowerCase();
  const name = String(file?.name || "").toLowerCase();
  return type.includes("png") || name.endsWith(".png");
}

function parseSizeFromParameters(parameters) {
  const match = String(parameters || "").match(/\bSize:\s*(\d+)\s*x\s*(\d+)/i);
  if (!match) {
    return {};
  }
  return {
    width: Number(match[1]),
    height: Number(match[2]),
  };
}

function parseStepsFromParameters(parameters) {
  const match = String(parameters || "").match(/\bSteps:\s*(\d+)/i);
  return match ? Number(match[1]) : undefined;
}

function resolveEncoderKind(inspectionData, parameters) {
  const payload = inspectionData?.payload && typeof inspectionData.payload === "object" ? inspectionData.payload : {};
  const profile = String(payload.profile || "").trim().toLowerCase();
  const promptEncoder = String(payload.prompt_encoder || "").trim().toLowerCase();
  if (SDXL_PROFILES.has(profile) || promptEncoder.includes("sdxl")) {
    return "sdxl";
  }
  if (/\b(?:VAE|Model):\s*[^,\n]*sdxl/i.test(parameters)) {
    return "sdxl";
  }
  return "sd15";
}

function readPositiveInteger(value, fallbackValue) {
  const numeric = Number(value);
  if (Number.isFinite(numeric) && numeric > 0) {
    return Math.round(numeric);
  }
  return fallbackValue;
}

async function buildA1111PngImportContext(file, inspectPngInfoRequest) {
  if (!file || !canReadFileBuffer(file) || !isLikelyPngFile(file)) {
    return null;
  }

  const buffer = await readFileBuffer(file);
  const metadata = extractPngTextMetadataFromArrayBuffer(buffer);
  if (hasEmbeddedComfyWorkflow(metadata)) {
    return null;
  }

  let parameters = metadata.parameters;
  let inspectionData = null;
  if (typeof inspectPngInfoRequest === "function") {
    try {
      const response = await inspectPngInfoRequest({ image_data: arrayBufferToDataUrl(buffer, file.type) });
      inspectionData = response?.data ?? response ?? null;
      if (inspectionData?.source_type && inspectionData.source_type !== "a1111") {
        return null;
      }
      parameters =
        parameters ??
        inspectionData?.metadata_items?.parameters ??
        inspectionData?.metadata_items?.Parameters ??
        inspectionData?.raw_parameters?.parameters ??
        "";
    } catch (_error) {
      inspectionData = null;
    }
  }

  // DEBUG HOTSPOT: real A1111 PNGs may store compressed text chunks that the lightweight frontend parser cannot see; trust the backend inspector when it identifies A1111.
  if (inspectionData?.source_type !== "a1111" && !isLikelyA1111Parameters(parameters)) {
    return null;
  }

  const payload = inspectionData?.payload && typeof inspectionData.payload === "object" ? inspectionData.payload : {};
  const size = parseSizeFromParameters(parameters);
  return {
    parameters,
    encoderKind: resolveEncoderKind(inspectionData, parameters),
    width: readPositiveInteger(payload.width, readPositiveInteger(size.width, 1024)),
    height: readPositiveInteger(payload.height, readPositiveInteger(size.height, 1024)),
    steps: readPositiveInteger(payload.steps, readPositiveInteger(parseStepsFromParameters(parameters), 10)),
  };
}

function getGraphNodes(graph) {
  if (Array.isArray(graph?._nodes)) {
    return graph._nodes;
  }
  if (Array.isArray(graph?.nodes)) {
    return graph.nodes;
  }
  return [];
}

function getNodeClass(node) {
  return String(node?.comfyClass || node?.type || node?.constructor?.comfyClass || "");
}

function setNodeClass(node, className, title) {
  node.type = className;
  node.comfyClass = className;
  node.title = title || className;
}

function findWidget(node, name) {
  return Array.isArray(node?.widgets) ? node.widgets.find((widget) => widget?.name === name) : undefined;
}

function getWidgetValue(node, name, fallbackValue = "") {
  return findWidget(node, name)?.value ?? fallbackValue;
}

function setWidgetValue(node, name, value) {
  node.widgets ??= [];
  const widget = findWidget(node, name);
  if (widget) {
    widget.value = value;
    return;
  }
  node.widgets.push({ name, value });
}

function readGraphLink(graph, linkId) {
  if (linkId == null) {
    return null;
  }
  if (graph?.links instanceof Map) {
    return graph.links.get(linkId) ?? null;
  }
  return graph?.links?.[linkId] ?? null;
}

function getGraphNodeById(graph, nodeId) {
  if (typeof graph?.getNodeById === "function") {
    return graph.getNodeById(nodeId);
  }
  return getGraphNodes(graph).find((node) => String(node.id) === String(nodeId)) ?? null;
}

function captureInputConnection(graph, node, inputIndex) {
  const link = readGraphLink(graph, node?.inputs?.[inputIndex]?.link);
  if (!link) {
    return null;
  }
  const sourceNode = getGraphNodeById(graph, link.origin_id);
  return sourceNode ? { sourceNode, sourceSlot: Number(link.origin_slot || 0) } : null;
}

function captureOutputConnections(graph, node, outputIndex) {
  const linkIds = node?.outputs?.[outputIndex]?.links ?? [];
  return linkIds
    .map((linkId) => readGraphLink(graph, linkId))
    .filter(Boolean)
    .map((link) => ({
      targetNode: getGraphNodeById(graph, link.target_id),
      targetSlot: Number(link.target_slot || 0),
    }))
    .filter((connection) => connection.targetNode);
}

function connectNodes(sourceNode, sourceSlot, targetNode, targetSlot) {
  if (typeof sourceNode?.connect === "function") {
    sourceNode.connect(sourceSlot, targetNode, targetSlot);
  }
}

function markGraphDirty(app, graph) {
  graph?.setDirtyCanvas?.(true, true);
  app?.canvas?.setDirty?.(true, true);
  app?.canvas?.setDirtyCanvas?.(true, true);
}

function patchSd15Node(node) {
  setNodeClass(node, "RookieUIA1111CLIPTextEncode", "RookieUI A1111 CLIP Text Encode");
  return true;
}

function patchSdxlNode({ app, graph, node, context, liteGraph }) {
  if (!liteGraph || typeof liteGraph.createNode !== "function" || typeof graph?.add !== "function" || typeof graph?.remove !== "function") {
    return false;
  }
  const replacement = liteGraph.createNode("RookieUIA1111CLIPTextEncodeSDXL");
  if (!replacement) {
    return false;
  }

  const inputConnection = captureInputConnection(graph, node, 0);
  const outputConnections = captureOutputConnections(graph, node, 0);
  const promptText = getWidgetValue(node, "text", "");

  setNodeClass(replacement, "RookieUIA1111CLIPTextEncodeSDXL", "RookieUI A1111 CLIP Text Encode SDXL");
  replacement.pos = Array.isArray(node.pos) ? [...node.pos] : node.pos;
  replacement.size = Array.isArray(node.size) ? [...node.size] : node.size;
  replacement.mode = node.mode;
  setWidgetValue(replacement, "width", context.width);
  setWidgetValue(replacement, "height", context.height);
  setWidgetValue(replacement, "crop_w", 0);
  setWidgetValue(replacement, "crop_h", 0);
  setWidgetValue(replacement, "target_width", context.width);
  setWidgetValue(replacement, "target_height", context.height);
  setWidgetValue(replacement, "text_g", promptText);
  setWidgetValue(replacement, "text_l", promptText);
  setWidgetValue(replacement, "steps", context.steps);

  graph.remove(node);
  graph.add(replacement);
  if (inputConnection) {
    connectNodes(inputConnection.sourceNode, inputConnection.sourceSlot, replacement, 0);
  }
  for (const outputConnection of outputConnections) {
    connectNodes(replacement, 0, outputConnection.targetNode, outputConnection.targetSlot);
  }
  markGraphDirty(app, graph);
  return true;
}

export function rewriteA1111CanvasImportEncoders({ app, context, windowRef = globalThis.window } = {}) {
  const graph = app?.rootGraph || app?.canvas?.graph;
  const nativeEncodeNodes = getGraphNodes(graph).filter((node) => getNodeClass(node) === "CLIPTextEncode");
  if (!graph || !nativeEncodeNodes.length) {
    return { rewritten: 0 };
  }

  let rewritten = 0;
  for (const node of [...nativeEncodeNodes]) {
    const patched =
      context?.encoderKind === "sdxl"
        ? patchSdxlNode({ app, graph, node, context, liteGraph: windowRef?.LiteGraph || globalThis.LiteGraph })
        : patchSd15Node(node);
    if (patched) {
      rewritten += 1;
    }
  }
  if (rewritten > 0) {
    markGraphDirty(app, graph);
  }
  return { rewritten };
}

export function installA1111CanvasImportParityPatch({ app, inspectPngInfoRequest, windowRef = globalThis.window } = {}) {
  if (!app || typeof app.handleFile !== "function" || app.__rookieuiA1111CanvasImportParityPatch) {
    return false;
  }

  const originalHandleFile = app.handleFile.bind(app);
  app.__rookieuiA1111CanvasImportParityPatch = true;
  app.handleFile = async function rookieuiA1111CanvasImportHandleFile(file, openSource, options) {
    let context = null;
    try {
      context = await buildA1111PngImportContext(file, inspectPngInfoRequest);
    } catch (_error) {
      context = null;
    }

    const result = await originalHandleFile(file, openSource, options);
    if (context) {
      // DEBUG HOTSPOT: ComfyUI's A1111 parameters fallback builds native CLIPTextEncode nodes; keep this post-import rewrite scoped to that fallback only.
      rewriteA1111CanvasImportEncoders({ app, context, windowRef });
    }
    return result;
  };
  return true;
}
