export function createPromptWorkbenchLifecycle() {
  let destroyed = false;
  const disposers = [];
  return {
    get destroyed() {
      return destroyed;
    },
    listen(target, eventName, handler, options) {
      target?.addEventListener?.(eventName, handler, options);
      disposers.push(() => target?.removeEventListener?.(eventName, handler, options));
    },
    destroy(...timerMaps) {
      if (destroyed) return;
      destroyed = true;
      disposers.splice(0).reverse().forEach((dispose) => dispose());
      for (const timerMap of timerMaps) {
        for (const timer of timerMap.values()) clearTimeout(timer);
        timerMap.clear();
      }
    },
  };
}
