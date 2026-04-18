import { createApp, reactive } from "vue";

import { loadRookieUIBootstrapData } from "../../web/rookieui_feature_registry.js";
import App from "./App.vue";
import { createVueSpikeLoaders } from "./fixtureLoaders.js";
import { createVueHostAdapterTabs } from "./mockHostAdapter.js";

const bootstrapState = await loadRookieUIBootstrapData(() => {}, {
  clientId: "vue-spike-client",
  loaders: createVueSpikeLoaders(),
});

const lifecycle = reactive({
  customMounts: 0,
  customUnmounts: 0,
  vueMounts: 0,
  vueUnmounts: 0,
});

const tabs = createVueHostAdapterTabs(bootstrapState, lifecycle);
window.__ROOKIEUI_VUE_SPIKE__ = {
  bootstrapState,
  lifecycle,
  tabIds: tabs.map((tab) => tab.id),
};

createApp(App, {
  bootstrapState,
  lifecycle,
  tabs,
}).mount("#app");
