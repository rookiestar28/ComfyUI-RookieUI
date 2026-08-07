// The backend manifest owns the family/profile contract. This module keeps the
// browser-only fallback provenance and stable projection copy intentionally
// small, static, and dependency-free.
export const DEFAULT_MODEL_FAMILY_FALLBACK_PROVENANCE = Object.freeze({
  canonical_owner: "python_manifest",
  contract_version: "model-family-20260713-effective-parameters",
  mode: "static-fail-closed",
  source: "fallback",
});

export function buildModelFamilyStableProjection(entry) {
  if (!entry || typeof entry !== "object") {
    return {};
  }
  return JSON.parse(JSON.stringify(entry));
}
