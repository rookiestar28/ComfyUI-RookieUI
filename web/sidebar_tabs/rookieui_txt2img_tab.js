export function createTxt2ImgTabDefinition(buildSection, bootstrapState, formRegistry) {
  return {
    id: "txt2img",
    label: "Txt2Img",
    render: (pane) => buildSection(pane, bootstrapState, formRegistry),
  };
}
