export function createActionButton(id, text) {
  const button = document.createElement("button");
  button.id = id;
  button.className = "rookieui-shell__button rookieui-shell__button--secondary";
  button.type = "button";
  button.textContent = text;
  return button;
}

export function createMiniActionButton(id, text) {
  const button = document.createElement("button");
  button.id = id;
  button.className = "rookieui-shell__mini-action";
  button.type = "button";
  button.textContent = text;
  return button;
}

const A1111_TOOL_EMOJI_MAP = Object.freeze({
  "pi-check-square": "📂",
  "pi-trash": "🗑️",
  "pi-file": "📋",
  "pi-pencil": "🖌️",
  "pi-folder-open": "📂",
  "pi-image": "🖼️",
  "pi-star": "📐",
  "pi-sliders-h": "♻️",
  "pi-images": "🗃️",
});

function resolveToolEmoji(iconToken) {
  if (typeof iconToken !== "string") {
    return "🔹";
  }
  const normalized = iconToken.trim();
  if (!normalized) {
    return "🔹";
  }
  // IMPORTANT: keep A1111-compatible emoji semantics here; replacing this with icon-font classes breaks the target ToolButton parity.
  return A1111_TOOL_EMOJI_MAP[normalized] ?? normalized;
}

export function createIconActionButton(id, iconToken, labelText, tone = "neutral") {
  const button = document.createElement("button");
  const safeTone = typeof tone === "string" && tone.trim() ? tone.trim() : "neutral";
  button.id = id;
  button.className = `rookieui-shell__mini-action rookieui-shell__mini-action--icon rookieui-shell__mini-action--tone-${safeTone}`;
  button.type = "button";
  button.title = labelText;
  button.setAttribute("aria-label", labelText);

  const icon = document.createElement("span");
  icon.className = "rookieui-shell__mini-action-icon";
  icon.textContent = resolveToolEmoji(iconToken);
  icon.setAttribute("aria-hidden", "true");
  button.appendChild(icon);
  return button;
}
