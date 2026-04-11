export function createQueueTabDefinition(buildSection, bootstrapState, formRegistry) {
  return {
    id: "queue",
    label: "Queue",
    render: (pane) => buildSection(pane, bootstrapState, formRegistry),
  };
}
