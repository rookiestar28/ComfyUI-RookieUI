<template>
  <main class="page-shell" data-testid="vue-spike-root">
    <section class="hero">
      <p class="eyebrow">R69 Vue Host-Adapter Feasibility Spike</p>
      <h1>Coexistence proof against the current RookieUI bootstrap contract</h1>
      <p class="lede">
        This spike keeps the shipped custom-render path intact while proving that a Vue sidebar tab
        can mount, unmount, and consume the same family-aware bootstrap state.
      </p>
    </section>

    <section class="toolbar">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        :data-testid="tab.type === 'vue' ? 'tab-vue' : 'tab-custom'"
        :class="['tab-button', { active: tab.id === activeTabId }]"
        type="button"
        @click="activeTabId = tab.id"
      >
        <span>{{ tab.title }}</span>
        <small>{{ tab.type }}</small>
      </button>
    </section>

    <section class="metrics">
      <article>
        <span>Vue mounts</span>
        <strong data-testid="metric-vue-mounts">{{ lifecycle.vueMounts }}</strong>
      </article>
      <article>
        <span>Vue unmounts</span>
        <strong>{{ lifecycle.vueUnmounts }}</strong>
      </article>
      <article>
        <span>Custom mounts</span>
        <strong>{{ lifecycle.customMounts }}</strong>
      </article>
      <article>
        <span>Custom unmounts</span>
        <strong data-testid="metric-custom-unmounts">{{ lifecycle.customUnmounts }}</strong>
      </article>
    </section>

    <section class="slot-frame">
      <ExtensionSlotHost :extension="activeExtension" />
    </section>
  </main>
</template>

<script setup>
import { computed, ref } from "vue";

import ExtensionSlotHost from "./ExtensionSlotHost.vue";

const props = defineProps({
  bootstrapState: {
    type: Object,
    required: true,
  },
  lifecycle: {
    type: Object,
    required: true,
  },
  tabs: {
    type: Array,
    required: true,
  },
});

const activeTabId = ref(props.tabs.find((tab) => tab.type === "vue")?.id ?? props.tabs[0]?.id ?? "");
const activeExtension = computed(() => props.tabs.find((tab) => tab.id === activeTabId.value) ?? props.tabs[0]);
</script>

<style scoped>
:global(body) {
  margin: 0;
  font-family: "Segoe UI", "Helvetica Neue", sans-serif;
  background:
    radial-gradient(circle at top left, rgba(32, 118, 255, 0.15), transparent 30%),
    linear-gradient(180deg, #f4f8fc 0%, #dde8f5 100%);
}

.page-shell {
  max-width: 1080px;
  margin: 0 auto;
  padding: 36px 20px 48px;
  color: #102034;
}

.hero {
  margin-bottom: 24px;
}

.eyebrow {
  margin: 0 0 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-size: 0.78rem;
  color: #58708e;
}

.hero h1 {
  margin: 0 0 12px;
  font-size: clamp(2rem, 4vw, 3.4rem);
  line-height: 1.05;
}

.lede {
  max-width: 760px;
  margin: 0;
  color: #42546d;
  font-size: 1.05rem;
}

.toolbar {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 18px;
}

.tab-button {
  border: 0;
  border-radius: 999px;
  padding: 12px 18px;
  background: rgba(255, 255, 255, 0.72);
  color: #19314f;
  cursor: pointer;
  display: inline-flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  box-shadow: 0 12px 30px rgba(16, 32, 52, 0.08);
}

.tab-button small {
  color: #6d819a;
}

.tab-button.active {
  background: linear-gradient(135deg, #0f63ff 0%, #2db0ff 100%);
  color: #fff;
}

.tab-button.active small {
  color: rgba(255, 255, 255, 0.82);
}

.metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}

.metrics article {
  border-radius: 16px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.74);
  box-shadow: 0 18px 40px rgba(16, 32, 52, 0.08);
}

.metrics span {
  display: block;
  font-size: 0.8rem;
  color: #5d7088;
}

.metrics strong {
  display: block;
  margin-top: 6px;
  font-size: 1.6rem;
}

.slot-frame {
  border-radius: 24px;
  padding: 18px;
  background: rgba(255, 255, 255, 0.55);
  box-shadow: 0 24px 60px rgba(16, 32, 52, 0.08);
}

:global(.custom-panel) {
  border-radius: 16px;
  padding: 20px;
  background: linear-gradient(180deg, #192637 0%, #2b415d 100%);
  color: #f5f8ff;
}

:global(.custom-panel h2) {
  margin: 0 0 8px;
}

:global(.custom-panel p) {
  margin: 0 0 16px;
  color: rgba(245, 248, 255, 0.8);
}

:global(.custom-panel dl) {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 0;
}

:global(.custom-panel dd) {
  margin: 6px 0 0;
  font-weight: 700;
}

@media (max-width: 800px) {
  .metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .metrics {
    grid-template-columns: 1fr;
  }
}
</style>
