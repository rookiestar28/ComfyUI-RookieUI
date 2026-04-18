import { defineComponent, h } from "vue";

import VueContractPanel from "./VueContractPanel.vue";

export function createVueHostAdapterTabs(bootstrapState, lifecycle) {
  return [
    {
      id: "rookieui-custom-spike",
      title: "Custom Extension",
      type: "custom",
      render(container) {
        lifecycle.customMounts += 1;
        container.innerHTML = "";
        const panel = document.createElement("section");
        panel.className = "custom-panel";
        panel.dataset.testid = "custom-extension-panel";
        panel.dataset.extensionType = "custom";
        panel.innerHTML = `
          <h2>Existing Custom Extension</h2>
          <p>Coexists beside the Vue proof without changing the shipped RookieUI render mode.</p>
          <dl>
            <div><dt>Profiles</dt><dd>${bootstrapState.capabilities?.parity?.profiles?.length ?? 0}</dd></div>
            <div><dt>Families</dt><dd>${bootstrapState.modelFamilyRegistry?.entries?.length ?? 0}</dd></div>
          </dl>
        `;
        container.appendChild(panel);
      },
      destroy() {
        lifecycle.customUnmounts += 1;
      },
    },
    {
      id: "rookieui-vue-spike",
      title: "Vue Extension",
      type: "vue",
      component: defineComponent({
        name: "RookieUIVueSpikePanel",
        render() {
          return h(VueContractPanel, {
            bootstrapState,
            lifecycle,
          });
        },
      }),
    },
  ];
}
