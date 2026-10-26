import { validateMossLayout, projectMossLayoutBoxes } from "./rookieui_moss_layout.js";

const emptyDraft = () => ({ enabled: false, elements: [] });
const make = (tag, text = "") => { const node = document.createElement(tag); node.textContent = text; return node; };

export function createMossLayoutEditor({ container, elements, onChange = () => {}, onModeChange = () => {} }) {
  const root = make("section");
  root.id = "rookieui-moss-layout";
  const enabled = Object.assign(make("input"), { type: "checkbox", id: "rookieui-moss-layout-enabled" });
  const toggle = make("label", "Layout guidance (experimental) ");
  toggle.style.cssText = "display:flex;justify-content:space-between;align-items:center;margin:8px 0";
  enabled.className = "rookieui-shell__checkbox";
  toggle.append(enabled);
  const help = make("p", "Author ordered boxes in normalized y0, x0, y1, x1 coordinates (0–1000). Text and box adherence depend on the model.");
  help.className = "rookieui-shell__status";
  const rows = make("div");
  rows.style.display = "grid";
  rows.style.gap = "8px";
  const add = Object.assign(make("button", "Add element"), { type: "button", id: "rookieui-moss-layout-add" });
  add.className = "rookieui-shell__button rookieui-shell__button--secondary";
  const error = make("p");
  error.id = "rookieui-moss-layout-error";
  error.setAttribute("role", "alert");
  error.className = "rookieui-shell__status";
  error.style.color = "var(--rookieui-danger, #b42318)";
  const preview = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  preview.id = "rookieui-moss-layout-preview";
  preview.setAttribute("role", "img");
  preview.setAttribute("aria-label", "Layout box projection at the selected output resolution");
  preview.style.cssText = "width:100%;max-height:240px;border:1px solid currentColor;margin-top:8px";
  root.append(toggle, help, rows, add, error, preview);
  container.append(root);
  let state = emptyDraft();
  let last = null;
  let valid = true;
  let hydrationError = "";

  const updatePreview = () => {
    const showDraft = state.enabled || state.elements.length > 0;
    [help, rows, add, preview].forEach(node => { node.style.display = !showDraft ? "none" : node === rows ? "grid" : ""; });
    try {
      validateMossLayout(state);
      const width = Number(elements.width.value), height = Number(elements.height.value);
      const boxes = projectMossLayoutBoxes(state, width, height);
      preview.setAttribute("viewBox", `0 0 ${width} ${height}`);
      preview.replaceChildren(...boxes.map((row, index) => {
        const group = document.createElementNS(preview.namespaceURI, "g");
        group.setAttribute("data-layout-preview-box", String(index + 1));
        const rect = document.createElementNS(preview.namespaceURI, "rect");
        const [y0, x0, y1, x1] = row.bbox;
        for (const [key, value] of Object.entries({ x: x0 + width / 2, y: y0 + height / 2, width: x1 - x0, height: y1 - y0, fill: "none", stroke: "#f97316", "stroke-width": 3 })) rect.setAttribute(key, String(value));
        const label = document.createElementNS(preview.namespaceURI, "text");
        label.setAttribute("x", String(x0 + width / 2 + 6));
        label.setAttribute("y", String(y0 + height / 2 + 24));
        label.setAttribute("fill", "currentColor");
        label.setAttribute("font-size", "20");
        label.textContent = `${index + 1}: ${row.kind}`;
        const title = document.createElementNS(preview.namespaceURI, "title");
        title.textContent = row.caption;
        group.append(title, rect, label);
        return group;
      }));
      valid = true;
      error.textContent = "";
    } catch (failure) {
      valid = false;
      error.textContent = failure instanceof Error ? failure.message : "Invalid MOSS layout.";
      preview.replaceChildren();
    }
    error.hidden = valid;
    enabled.setAttribute("aria-invalid", String(!valid));
    const badRow = /element (\d+):/.exec(error.textContent);
    rows.querySelectorAll("[data-layout-field]").forEach(input => {
      const name = input.getAttribute("data-layout-field");
      const affected = !valid && badRow && input.closest("[data-layout-row]")?.getAttribute("data-layout-row") === String(Number(badRow[1]) - 1) &&
        (error.textContent.includes(name) || error.textContent.includes("bbox") && ["y0", "x0", "y1", "x1"].includes(name));
      input.setAttribute("aria-invalid", String(Boolean(affected)));
      input.setAttribute("aria-describedby", error.id);
    });
    add.disabled = state.elements.length >= 32;
  };

  const commit = () => {
    elements.mossLayoutState.value = JSON.stringify(state);
    last = elements.mossLayoutState.value;
    updatePreview();
    onChange();
  };
  const renderRows = () => {
    rows.replaceChildren();
    enabled.checked = state.enabled === true;
    state.elements.forEach((row, index) => {
      const group = make("fieldset");
      group.setAttribute("data-layout-row", String(index));
      group.style.cssText = "min-width:0;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:8px 0;padding:10px;border:1px solid currentColor;border-radius:8px";
      group.append(make("legend", `Element ${index + 1}`));
      const field = (name, node, callback) => {
        const label = make("label", `${name} `);
        label.style.cssText = `display:grid;gap:4px;grid-column:${["y0", "x0", "y1", "x1"].includes(name) ? "auto" : "1 / -1"}`;
        node.setAttribute("aria-label", `Element ${index + 1} ${name}`);
        node.setAttribute("data-layout-field", name.toLowerCase());
        node.style.cssText = "width:100%;box-sizing:border-box";
        node.className = node.tagName === "SELECT" ? "rookieui-shell__select" : node.tagName === "TEXTAREA" ? "rookieui-shell__textarea" : "rookieui-shell__input";
        node.addEventListener("input", () => { callback(); commit(); });
        label.append(node);
        group.append(label);
        return node;
      };
      const kind = make("select");
      ["object", "text", "character"].forEach(value => kind.append(new Option(value, value)));
      kind.value = row.kind;
      const caption = Object.assign(make("textarea"), { value: row.caption ?? "", rows: 2 });
      const text = Object.assign(make("textarea"), { value: row.text ?? "", rows: 2, disabled: row.kind !== "text" });
      field("Kind", kind, () => {
        row.kind = kind.value;
        text.disabled = row.kind !== "text";
        if (row.kind === "text") row.text = text.value; else delete row.text;
      });
      field("Caption", caption, () => { row.caption = caption.value; });
      field("Text", text, () => { row.text = text.value; });
      ["y0", "x0", "y1", "x1"].forEach((name, edge) => {
        const input = Object.assign(make("input"), { type: "number", min: "0", max: "1000", step: "any", value: String(row.bbox?.[edge] ?? "") });
        field(name, input, () => { row.bbox[edge] = input.value === "" ? "" : Number(input.value); });
      });
      const palette = Object.assign(make("input"), { type: "text", value: (row.palette ?? []).join(", ") });
      field("Palette", palette, () => {
        const values = palette.value.split(",").map(value => value.trim());
        if (palette.value.trim()) row.palette = values; else delete row.palette;
      });
      const actions = make("div");
      actions.style.cssText = "display:flex;flex-wrap:wrap;gap:6px;grid-column:1 / -1";
      for (const [name, label, offset] of [["up", "Move up", -1], ["down", "Move down", 1], ["delete", "Delete", 0]]) {
        const button = Object.assign(make("button", label), { type: "button" });
        button.className = "rookieui-shell__button rookieui-shell__button--secondary";
        button.setAttribute("data-layout-action", name);
        button.setAttribute("aria-label", `${label} element ${index + 1}`);
        button.disabled = name === "up" && index === 0 || name === "down" && index === state.elements.length - 1;
        button.addEventListener("click", () => {
          if (name === "delete") state.elements.splice(index, 1);
          else [state.elements[index], state.elements[index + Number(offset)]] = [state.elements[index + Number(offset)], state.elements[index]];
          commit(); renderRows(); add.focus();
        });
        actions.append(button);
      }
      group.append(actions);
      rows.append(group);
    });
  };
  enabled.addEventListener("change", () => { state.enabled = enabled.checked; onModeChange(state.enabled); commit(); });
  add.addEventListener("click", () => {
    if (state.elements.length >= 32) return;
    state.elements.push({ kind: "object", caption: "", bbox: [100, 100, 900, 900] });
    commit(); renderRows(); rows.lastElementChild?.querySelector("textarea")?.focus();
  });
  [elements.width, elements.height].forEach(input => input.addEventListener("input", () => { updatePreview(); onChange(); }));
  const sync = ({ resetDefaults = false, payload = null } = {}) => {
    if (resetDefaults) elements.mossLayoutState.value = "";
    if (payload?.moss_options) elements.mossLayoutState.value = Object.hasOwn(payload.moss_options, "layout") ? JSON.stringify(payload.moss_options.layout) : "";
    if (last !== elements.mossLayoutState.value) {
      last = elements.mossLayoutState.value;
      try {
        const decoded = last ? JSON.parse(last) : emptyDraft();
        // IMPORTANT: hydrate editable invalid fields before validating bounds;
        // discarding a bad draft here loses authored content after remount.
        if (!decoded || typeof decoded.enabled !== "boolean" || !Array.isArray(decoded.elements) || decoded.elements.length > 32 ||
          decoded.elements.some(row => !row || typeof row !== "object" || !Array.isArray(row.bbox) || row.bbox.length !== 4 ||
            typeof row.caption !== "string" || (row.palette !== undefined && !Array.isArray(row.palette)))) {
          throw new Error("MOSS layout draft has invalid fields; select a preset to reset it.");
        }
        state = decoded;
        hydrationError = "";
        renderRows();
      } catch (failure) {
        valid = false; error.hidden = false;
        hydrationError = failure instanceof Error ? failure.message : "Invalid MOSS layout.";
        error.textContent = hydrationError;
        return;
      }
    }
    if (hydrationError) { valid = false; error.hidden = false; error.textContent = hydrationError; return; }
    updatePreview();
  };
  return { sync, valid: () => valid };
}
