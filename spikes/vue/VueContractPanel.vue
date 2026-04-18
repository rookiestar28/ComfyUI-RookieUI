<template>
  <section class="panel" data-testid="vue-extension-panel" data-extension-type="vue">
    <header class="panel-header">
      <h2>Vue Host Adapter</h2>
      <p>Consumes the same RookieUI bootstrap contract without replacing the shipped shell.</p>
    </header>
    <dl class="summary-grid">
      <div>
        <dt>Family registry contract</dt>
        <dd>{{ bootstrapState.modelFamilyRegistry.contract_version }}</dd>
      </div>
      <div>
        <dt>Host surfaces</dt>
        <dd>{{ hostSurfaces }}</dd>
      </div>
      <div>
        <dt>Preset count</dt>
        <dd>{{ presetCount }}</dd>
      </div>
      <div>
        <dt>Queue client</dt>
        <dd>{{ queueClient }}</dd>
      </div>
    </dl>
    <ul class="family-list">
      <li v-for="entry in familyEntries" :key="entry.id">
        <strong>{{ entry.title }}</strong>
        <span>{{ entry.id }}</span>
        <span>{{ entry.support_tier }}</span>
        <span>{{ entry.primary_model_category }}</span>
      </li>
    </ul>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted } from "vue";

const props = defineProps({
  bootstrapState: {
    type: Object,
    required: true,
  },
  lifecycle: {
    type: Object,
    required: true,
  },
});

const familyEntries = computed(() => props.bootstrapState?.modelFamilyRegistry?.entries ?? []);
const hostSurfaces = computed(() => (props.bootstrapState?.capabilities?.host_surfaces ?? []).join(", ") || "none");
const presetCount = computed(() => props.bootstrapState?.presets?.presets?.length ?? 0);
const queueClient = computed(() => props.bootstrapState?.queue?.clientId ?? "missing");

onMounted(() => {
  props.lifecycle.vueMounts += 1;
});

onBeforeUnmount(() => {
  props.lifecycle.vueUnmounts += 1;
});
</script>

<style scoped>
.panel {
  border: 1px solid #d0d8e3;
  border-radius: 16px;
  background: linear-gradient(180deg, #fbfdff 0%, #eef4fb 100%);
  padding: 20px;
  color: #132033;
}

.panel-header h2 {
  margin: 0 0 6px;
  font-size: 1.15rem;
}

.panel-header p {
  margin: 0 0 18px;
  color: #42546d;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 0 0 18px;
}

.summary-grid div {
  padding: 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.75);
}

.summary-grid dt {
  font-size: 0.8rem;
  color: #5a6d86;
}

.summary-grid dd {
  margin: 6px 0 0;
  font-weight: 600;
}

.family-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.family-list li {
  display: grid;
  grid-template-columns: minmax(0, 2fr) repeat(3, minmax(0, 1fr));
  gap: 10px;
  align-items: center;
  padding: 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.88);
}

@media (max-width: 800px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .family-list li {
    grid-template-columns: 1fr;
  }
}
</style>
