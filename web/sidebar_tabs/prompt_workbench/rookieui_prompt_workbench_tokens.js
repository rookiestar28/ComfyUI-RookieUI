let tokenSequence = 0;

export function normalizeDomIdPart(value) {
  return String(value ?? "")
    .trim()
    .replace(/[^A-Za-z0-9_-]+/g, "-") || "option";
}

export function normalizeTokenText(text) {
  return String(text ?? "").trim();
}

export function classifyPromptToken(text) {
  const normalized = normalizeTokenText(text);
  const lower = normalized.toLowerCase();
  if (lower === "break") {
    return "break";
  }
  if (lower === "and" || lower.startsWith("and ")) {
    return "and";
  }
  if (lower.startsWith("<lora:")) {
    return "lora";
  }
  if (lower.startsWith("<lyco:") || lower.startsWith("<lycoris:")) {
    return "lycoris";
  }
  if (lower.startsWith("embedding:")) {
    return "embedding";
  }
  if (lower.startsWith("[") && lower.endsWith("]") && lower.includes(":")) {
    return "schedule";
  }
  if (extractTokenWeight(normalized) !== null || (normalized.startsWith("(") && normalized.endsWith(")"))) {
    return "weighted";
  }
  return "plain";
}

export function extractTokenWeight(text) {
  const match = normalizeTokenText(text).match(/^\((.+):([+-]?(?:\d+(?:\.\d+)?|\.\d+))\)$/);
  if (!match) {
    return null;
  }
  const value = Number.parseFloat(match[2]);
  return Number.isFinite(value) ? value : null;
}

export function createToken(
  text,
  {
    disabled = false,
    selected = false,
    translatedText = "",
    scope = "prompt",
    orderIndex = 0,
  } = {},
) {
  tokenSequence += 1;
  const rawText = normalizeTokenText(text);
  return {
    id: `pw-token-${tokenSequence}`,
    text: rawText,
    raw_text: rawText,
    normalized_text: rawText.toLowerCase(),
    scope: String(scope ?? "prompt").trim() || "prompt",
    order_index: Number.isInteger(orderIndex) ? orderIndex : 0,
    disabled: Boolean(disabled),
    selected: Boolean(selected),
    translated_text: String(translatedText ?? ""),
    keyword_family: classifyPromptToken(rawText),
    weight: extractTokenWeight(rawText),
  };
}

export function normalizeStatePayload(namespace, payload) {
  return {
    namespace,
    workbench_open: Boolean(payload?.workbench_open),
    active_panel: String(payload?.active_panel ?? "editor").trim() || "editor",
    draft_prompt: String(payload?.draft_prompt ?? ""),
    selected_entry_id: String(payload?.selected_entry_id ?? ""),
  };
}

export function normalizePromptEntry(entry) {
  return {
    id: String(entry?.id ?? "").trim() || `pw-entry-${Date.now()}`,
    label: String(entry?.label ?? "").trim(),
    prompt_text: String(entry?.prompt_text ?? "").trim(),
    tag_tokens: Array.isArray(entry?.tag_tokens) ? entry.tag_tokens.map((token) => normalizeTokenText(token)).filter(Boolean) : [],
    token_payloads: Array.isArray(entry?.token_payloads) ? entry.token_payloads.map(normalizePersistedTokenPayload).filter(Boolean) : [],
    created_at: Number(entry?.created_at ?? 0) || 0,
  };
}

export function normalizePersistedTokenPayload(token) {
  if (!token || typeof token !== "object") {
    return null;
  }
  const rawText = normalizeTokenText(token.raw_text ?? token.text);
  if (!rawText) {
    return null;
  }
  return {
    raw_text: rawText,
    normalized_text: normalizeTokenText(token.normalized_text) || rawText.toLowerCase(),
    scope: normalizeTokenText(token.scope),
    order_index: Number.isInteger(token.order_index) ? token.order_index : 0,
    disabled: Boolean(token.disabled),
    selected: Boolean(token.selected),
    translated_text: String(token.translated_text ?? ""),
    keyword_family: normalizeTokenText(token.keyword_family) || classifyPromptToken(rawText),
    weight: Number.isFinite(Number(token.weight)) ? Number(token.weight) : null,
  };
}

export function setText(node, value) {
  if (node) {
    node.textContent = String(value ?? "");
  }
}

export function countPromptUnits(value) {
  const trimmed = String(value ?? "").trim();
  if (!trimmed) {
    return 0;
  }
  return trimmed.split(/[\s,]+/).filter(Boolean).length;
}

export function splitPromptTokenText(text) {
  const source = String(text ?? "");
  const tokens = [];
  let current = "";
  let escaped = false;
  let parenDepth = 0;
  let bracketDepth = 0;
  let angleDepth = 0;

  for (const char of source) {
    if (escaped) {
      current += char;
      escaped = false;
      continue;
    }
    if (char === "\\") {
      current += char;
      escaped = true;
      continue;
    }
    if (char === "<") {
      angleDepth += 1;
      current += char;
      continue;
    }
    if (char === ">" && angleDepth > 0) {
      angleDepth -= 1;
      current += char;
      continue;
    }
    if (char === "(" && angleDepth === 0) {
      parenDepth += 1;
      current += char;
      continue;
    }
    if (char === ")" && parenDepth > 0 && angleDepth === 0) {
      parenDepth -= 1;
      current += char;
      continue;
    }
    if (char === "[" && angleDepth === 0) {
      bracketDepth += 1;
      current += char;
      continue;
    }
    if (char === "]" && bracketDepth > 0 && angleDepth === 0) {
      bracketDepth -= 1;
      current += char;
      continue;
    }
    if ((char === "," || char === "\n") && parenDepth === 0 && bracketDepth === 0 && angleDepth === 0) {
      const normalized = normalizeTokenText(current);
      if (normalized) {
        tokens.push(normalized);
      }
      current = "";
      continue;
    }
    current += char;
  }

  const normalized = normalizeTokenText(current);
  if (normalized) {
    tokens.push(normalized);
  }
  return tokens;
}

export function parsePromptTokens(text, { scope = "prompt" } = {}) {
  return splitPromptTokenText(text).map((entry, index) => createToken(entry, { scope, orderIndex: index }));
}

export function buildPromptTextFromTokens(tokens) {
  return (Array.isArray(tokens) ? tokens : [])
    .filter((token) => token && !token.disabled && normalizeTokenText(token.raw_text ?? token.text))
    .map((token) => normalizeTokenText(token.raw_text ?? token.text))
    .join(", ");
}

export function formatTokenWeight(value) {
  const rounded = Math.max(0, Math.round(Number(value) * 100) / 100);
  return String(rounded).replace(/\.0+$/, "").replace(/(\.\d*[1-9])0+$/, "$1");
}

export function adjustPromptTokenWeight(text, delta) {
  const normalized = normalizeTokenText(text);
  if (!normalized) {
    return "";
  }
  const match = normalized.match(/^\((.+):([+-]?(?:\d+(?:\.\d+)?|\.\d+))\)$/);
  if (match) {
    return `(${match[1]}:${formatTokenWeight(Number.parseFloat(match[2]) + delta)})`;
  }
  return `(${normalized}:${delta >= 0 ? "1.1" : "0.9"})`;
}

export function updateTokenText(token, nextText) {
  const rawText = normalizeTokenText(nextText);
  token.text = rawText;
  token.raw_text = rawText;
  token.normalized_text = rawText.toLowerCase();
  token.keyword_family = classifyPromptToken(rawText);
  token.weight = extractTokenWeight(rawText);
}

export function formatPromptText(text, formattingRules) {
  let nextText = String(text ?? "");
  if (formattingRules?.normalize_spacing) {
    nextText = nextText
      .split(/[\n,]+/)
      .map((entry) => entry.trim())
      .filter(Boolean)
      .join(", ");
  }
  if (formattingRules?.dedupe_commas) {
    const seen = new Set();
    nextText = nextText
      .split(/[\n,]+/)
      .map((entry) => entry.trim())
      .filter(Boolean)
      .filter((entry) => {
        const key = entry.toLowerCase();
        if (seen.has(key)) {
          return false;
        }
        seen.add(key);
        return true;
      })
      .join(", ");
  }
  if (formattingRules?.trim_outer_whitespace) {
    nextText = nextText.trim();
  }
  return nextText;
}

export function buildEntryLabel(scope, promptText) {
  const preview = String(promptText ?? "").trim();
  if (!preview) {
    return scope === "negative" ? "Negative Prompt" : "Prompt";
  }
  const prefix = scope === "negative" ? "Negative" : "Prompt";
  return `${prefix}: ${preview.slice(0, 48)}`;
}

export function clearChildren(node) {
  if (node) {
    node.replaceChildren();
  }
}
export function serializeTokenPayload(token, index, fallbackScope = "prompt") {
  const rawText = normalizeTokenText(token?.raw_text ?? token?.text);
  if (!rawText) {
    return null;
  }
  return {
    raw_text: rawText,
    normalized_text: normalizeTokenText(token.normalized_text) || rawText.toLowerCase(),
    scope: normalizeTokenText(token.scope) || fallbackScope,
    order_index: Number.isInteger(token.order_index) ? token.order_index : index,
    disabled: Boolean(token.disabled),
    selected: Boolean(token.selected),
    translated_text: String(token.translated_text ?? ""),
    keyword_family: normalizeTokenText(token.keyword_family) || classifyPromptToken(rawText),
    weight: Number.isFinite(Number(token.weight)) ? Number(token.weight) : null,
  };
}

export function serializeTokenPayloads(tokens, fallbackScope = "prompt") {
  return (Array.isArray(tokens) ? tokens : [])
    .map((token, index) => serializeTokenPayload(token, index, fallbackScope))
    .filter(Boolean);
}

export function buildCollectionItem(scope, promptText, tokens) {
  const tokenPayloads = serializeTokenPayloads(tokens, scope);
  return {
    label: buildEntryLabel(scope, promptText),
    prompt_text: String(promptText ?? "").trim(),
    tag_tokens: tokenPayloads.filter((token) => !token.disabled).map((token) => token.raw_text),
    token_payloads: tokenPayloads,
  };
}
