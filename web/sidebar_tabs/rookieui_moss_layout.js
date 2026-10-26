/** @typedef {import('../types/rookieui_api_contracts').RookieUIMossLayout} MossLayout */

function record(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function validText(value, limit) {
  return typeof value === "string" && Array.from(value).length <= limit &&
    !Array.from(value).some(char => { const code = char.codePointAt(0); return code >= 0xd800 && code <= 0xdfff; });
}

/** Validate authored data without coercing coordinates, booleans or text. @returns {MossLayout} */
export function validateMossLayout(value) {
  if (!record(value) || Object.keys(value).sort().join() !== "elements,enabled" ||
    typeof value.enabled !== "boolean" || !Array.isArray(value.elements) || value.elements.length > 32) {
    throw new Error("MOSS layout requires enabled and at most 32 elements.");
  }
  for (const [index, row] of value.elements.entries()) {
    const fail = reason => { throw new Error(`MOSS layout element ${index + 1}: ${reason}`); };
    if (!record(row) || !["kind", "caption", "bbox"].every(key => Object.hasOwn(row, key)) ||
      Object.keys(row).some(key => !["kind", "caption", "bbox", "text", "palette"].includes(key))) fail("invalid fields.");
    if (!["object", "text", "character"].includes(row.kind)) fail("invalid kind.");
    if (!validText(row.caption, 2048)) fail("caption must be at most 2048 Unicode characters.");
    if (row.kind !== "text" && Object.hasOwn(row, "text")) fail("rendered text requires text kind.");
    if (Object.hasOwn(row, "text") && !validText(row.text, 1024)) fail("text must be at most 1024 Unicode characters.");
    if (!Array.isArray(row.bbox) || row.bbox.length !== 4 || row.bbox.some(v => typeof v !== "number" || !Number.isFinite(v) || v < 0 || v > 1000) ||
      row.bbox[0] >= row.bbox[2] || row.bbox[1] >= row.bbox[3]) fail("bbox requires 0..1000 y0,x0,y1,x1 with positive area.");
    if (Object.hasOwn(row, "palette") && (!Array.isArray(row.palette) || row.palette.length > 8 ||
      row.palette.some(color => typeof color !== "string" || !/^#[0-9a-fA-F]{6}$/.test(color)))) fail("palette requires at most eight #RRGGBB colors.");
  }
  if (new TextEncoder().encode(JSON.stringify(value)).length > 128 * 1024) throw new Error("MOSS layout exceeds 128 KiB of UTF-8 JSON.");
  return structuredClone(value);
}

export function readMossLayoutState(elements) {
  const raw = elements.mossLayoutState?.value;
  if (!raw) return null;
  let value;
  try { value = JSON.parse(raw); } catch (_error) { throw new Error("MOSS layout draft contains invalid JSON."); }
  return validateMossLayout(value);
}

/** @param {MossLayout} value */
export function projectMossLayoutBoxes(value, width, height) {
  validateMossLayout(value);
  if (![width, height].every(d => Number.isInteger(d) && d >= 64 && d <= 2048 && d % 16 === 0)) {
    throw new Error("MOSS layout dimensions must be 64..2048 and divisible by 16.");
  }
  return value.elements.map(row => ({ ...row, bbox: row.bbox.map((edge, index) => {
    const size = index % 2 === 0 ? height : width;
    // IMPORTANT: enclosing native yxyx edges use rounded pixel values before
    // floor/ceil and center subtraction; integer truncation shrinks boxes.
    const pixel = Number((edge * size / 1000).toFixed(9));
    return (index < 2 ? Math.floor(pixel) : Math.ceil(pixel)) - Math.floor(size / 2);
  }) }));
}
