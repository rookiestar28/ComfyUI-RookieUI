export function createPngInfoTabDefinition(buildSection, bootstrapState, formRegistry) {
  return {
    id: "pnginfo",
    label: "PNG Info",
    render: (pane) => buildSection(pane, bootstrapState, formRegistry),
  };
}
