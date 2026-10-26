// @vitest-environment jsdom
import { expect, test } from "vitest";
import { validateMossLayout, projectMossLayoutBoxes, readMossLayoutState } from "../../web/sidebar_tabs/rookieui_moss_layout.js";
import { createMossLayoutEditor } from "../../web/sidebar_tabs/rookieui_moss_layout_editor.js";

const element = (overrides = {}) => ({ kind: "text", caption: "中文 caption", text: "<script>literal</script>\n字", bbox: [200.1, 100.1, 799.9, 899.9], ...overrides });
test("strict layout validation and rectangular projection match native enclosing edges", () => {
  const value = { enabled: true, elements: [element()] };
  expect(validateMossLayout(value)).toEqual(value);
  expect(projectMossLayoutBoxes(value, 768, 512)[0].bbox).toEqual([-154, -308, 154, 308]);
  expect(projectMossLayoutBoxes(value, 1024, 768)[0].bbox).toEqual([-231, -410, 231, 410]);
  for (const bad of [{ ...value, extra: 1 }, { ...value, enabled: "true" },
    { enabled: false, elements: [element({ bbox: [0, 0, 0, 1000] })] },
    { ...value, elements: [element({ bbox: [false, 0, 1, 1] })] },
    { ...value, elements: [element({ text: "x".repeat(1025) })] },
    { ...value, elements: Array.from({ length: 33 }, () => element()) },
    { ...value, elements: Array.from({ length: 32 }, () => element({ caption: "字".repeat(2048) })) }]) {
    expect(() => validateMossLayout(bad)).toThrow(/MOSS/);
  }
  expect(() => projectMossLayoutBoxes(value, 65, 512)).toThrow(/16/);
  expect(() => readMossLayoutState({ mossLayoutState: { value: "{" } })).toThrow(/MOSS/);
});

test("form edits CRUD reorder preview and invalid-state admission remain synchronized and literal", () => {
  const container = document.createElement("div");
  document.body.replaceChildren(container);
  const input = value => Object.assign(document.createElement("input"), { value });
  const elements = { mossLayoutState: input(""), width: input("768"), height: input("512") };
  let changes = 0;
  const editor = createMossLayoutEditor({ container, elements, onChange: () => { changes++; } });
  editor.sync();
  container.querySelector("#rookieui-moss-layout-enabled").click();
  container.querySelector("#rookieui-moss-layout-add").click();
  const caption = container.querySelector('[data-layout-field="caption"]');
  caption.value = "<img src=x onerror=alert(1)> 中文";
  caption.dispatchEvent(new Event("input"));
  expect(container.querySelector("img")).toBeNull();
  expect(readMossLayoutState(elements).elements[0].caption).toBe(caption.value);
  expect(editor.valid()).toBe(true);
  const y0 = container.querySelector('[data-layout-field="y0"]');
  y0.value = "1000";
  y0.dispatchEvent(new Event("input"));
  expect(editor.valid()).toBe(false);
  expect(container.querySelector('[role="alert"]').textContent).toContain("bbox");
  expect(caption.value).toContain("中文");
  y0.value = "0";
  y0.dispatchEvent(new Event("input"));
  container.querySelector("#rookieui-moss-layout-add").click();
  const captions = container.querySelectorAll('[data-layout-field="caption"]');
  captions[1].value = "second";
  captions[1].dispatchEvent(new Event("input"));
  container.querySelectorAll('[data-layout-action="up"]')[1].click();
  expect(readMossLayoutState(elements).elements.map(row => row.caption)).toEqual(["second", caption.value]);
  expect(container.querySelectorAll("[data-layout-preview-box]")).toHaveLength(2);
  container.querySelectorAll('[data-layout-action="delete"]')[0].click();
  expect(readMossLayoutState(elements).elements).toHaveLength(1);
  elements.width.value = "1024";
  elements.width.dispatchEvent(new Event("input"));
  expect(container.querySelector("#rookieui-moss-layout-preview").getAttribute("viewBox")).toBe("0 0 1024 512");
  expect(changes).toBeGreaterThan(5);
  const state = JSON.parse(elements.mossLayoutState.value);
  editor.sync({ resetDefaults: true });
  expect(elements.mossLayoutState.value).toBe("");
  editor.sync({ payload: { moss_options: { layout: state } } });
  expect(readMossLayoutState(elements)).toEqual(state);
  expect(editor.valid()).toBe(true);
});
