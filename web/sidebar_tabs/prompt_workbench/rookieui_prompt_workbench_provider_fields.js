export function createProviderConfigInput({
  fieldSpec,
  fieldKey,
  providerConfig,
  idPrefix,
  onChange,
}) {
  const input = document.createElement("input");
  const isBoolean = String(fieldSpec?.value_type ?? "string") === "boolean";
  input.type = isBoolean ? "checkbox" : fieldSpec?.secret ? "password" : "text";
  input.id = `${idPrefix}-assist-config-${fieldKey}`;
  input.className = "rookieui-shell__input";
  input.placeholder = String(fieldSpec?.placeholder ?? "");
  if (isBoolean) {
    input.checked = providerConfig[fieldKey] === true || (
      providerConfig[fieldKey] === undefined && fieldSpec?.default === true
    );
  } else {
    input.value = String(providerConfig[fieldKey] ?? fieldSpec?.default ?? "");
  }
  input.addEventListener("change", () => {
    onChange?.(isBoolean ? input.checked : input.value);
  });
  return input;
}
