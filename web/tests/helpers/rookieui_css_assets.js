import { readFileSync } from "node:fs";
import { resolve } from "node:path";

export const ROOKIEUI_SHIPPED_CSS_ASSETS = Object.freeze([
  "rookieui_tokens.css",
  "rookieui_shell_foundation.css",
  "rookieui_panes.css",
  "rookieui_controlnet.css",
]);

export function readRookieUIShippedCss() {
  return ROOKIEUI_SHIPPED_CSS_ASSETS.map((asset) => readFileSync(resolve(process.cwd(), "web", asset), "utf8")).join("\n");
}
