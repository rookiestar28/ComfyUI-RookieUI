export function createImg2ImgTabDefinition(buildSection, bootstrapState, formRegistry) {
  return {
    id: "img2img",
    label: "Img2Img",
    render: (pane) => buildSection(pane, bootstrapState, formRegistry),
  };
}
