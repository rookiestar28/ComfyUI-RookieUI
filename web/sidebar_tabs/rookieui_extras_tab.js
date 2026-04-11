export function createExtrasTabDefinition(buildSection, bootstrapState, formRegistry) {
  return {
    id: "extras",
    label: "Extras",
    render: (pane) => buildSection(pane, bootstrapState, formRegistry),
  };
}
