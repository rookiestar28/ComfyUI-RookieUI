export function collectPromptWorkbenchSuggestions({ favorites = [], history = [], catalogPayload = null, normalizeFragment } = {}) {
  const seen = new Set();
  const suggestions = [];
  const pushSuggestion = (source, label, fragment) => {
    const normalizedFragment = normalizeFragment(fragment);
    if (!normalizedFragment || seen.has(normalizedFragment)) return;
    seen.add(normalizedFragment);
    suggestions.push({ source, label: String(label ?? normalizedFragment), fragment: normalizedFragment });
  };

  (Array.isArray(favorites) ? favorites : []).slice(0, 3).forEach((entry) => {
    pushSuggestion("favorites", entry.label || "Favorite", entry.prompt_text);
  });
  (Array.isArray(history) ? history : []).slice(0, 3).forEach((entry) => {
    pushSuggestion("history", entry.label || "History", entry.prompt_text);
  });
  (Array.isArray(catalogPayload?.tagcomplete?.entries) ? catalogPayload.tagcomplete.entries : []).slice(0, 6).forEach((entry) => {
    pushSuggestion("tagcomplete", entry?.label ?? entry?.tag, entry?.insert_token ?? entry?.tag ?? entry?.label);
  });
  return suggestions.slice(0, 8);
}
