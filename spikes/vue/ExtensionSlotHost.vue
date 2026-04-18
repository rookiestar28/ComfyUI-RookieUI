<template>
  <component :is="extension.component" v-if="extension.type === 'vue'" />
  <div v-else ref="customHost" />
</template>

<script setup>
import { nextTick, onBeforeUnmount, ref, watch } from "vue";

const props = defineProps({
  extension: {
    type: Object,
    required: true,
  },
});

const customHost = ref(null);
let mountedCustomId = null;

function destroyCustomExtension(extension) {
  if (!extension || extension.type !== "custom") {
    return;
  }
  if (mountedCustomId === extension.id && typeof extension.destroy === "function") {
    extension.destroy();
  }
  if (customHost.value) {
    customHost.value.innerHTML = "";
  }
  mountedCustomId = null;
}

function renderCustomExtension(extension) {
  if (!extension || extension.type !== "custom" || !customHost.value) {
    return;
  }
  if (mountedCustomId === extension.id) {
    return;
  }
  customHost.value.innerHTML = "";
  extension.render(customHost.value);
  mountedCustomId = extension.id;
}

watch(
  () => props.extension,
  async (nextExtension, previousExtension) => {
    if (previousExtension?.type === "custom" && previousExtension.id !== nextExtension?.id) {
      destroyCustomExtension(previousExtension);
    }
    await nextTick();
    renderCustomExtension(nextExtension);
  },
  { immediate: true },
);

watch(customHost, async () => {
  await nextTick();
  renderCustomExtension(props.extension);
});

onBeforeUnmount(() => {
  destroyCustomExtension(props.extension);
});
</script>
