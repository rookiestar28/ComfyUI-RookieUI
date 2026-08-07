export function createPromptWorkbenchLifecycle() {
  let destroyed = false;
  const disposers = [];
  const timers = new Set();
  const abortControllers = new Set();
  const ownedNodes = new Set();

  const removeDisposer = (disposer) => {
    const index = disposers.indexOf(disposer);
    if (index >= 0) disposers.splice(index, 1);
  };

  return {
    get destroyed() {
      return destroyed;
    },
    listen(target, eventName, handler, options) {
      if (destroyed || !target?.addEventListener || typeof handler !== "function") {
        return () => {};
      }
      target?.addEventListener?.(eventName, handler, options);
      const dispose = () => target?.removeEventListener?.(eventName, handler, options);
      disposers.push(dispose);
      return () => {
        removeDisposer(dispose);
        dispose();
      };
    },
    timeout(callback, delay = 0) {
      if (destroyed || typeof callback !== "function") {
        return null;
      }
      const timer = setTimeout(() => {
        timers.delete(timer);
        if (!destroyed) callback();
      }, delay);
      timers.add(timer);
      return timer;
    },
    interval(callback, delay = 0) {
      if (destroyed || typeof callback !== "function") {
        return null;
      }
      const timer = setInterval(() => {
        if (!destroyed) callback();
      }, delay);
      timers.add(timer);
      return timer;
    },
    cancel(timer) {
      if (timer === null || timer === undefined) return;
      clearTimeout(timer);
      clearInterval(timer);
      timers.delete(timer);
    },
    trackAbortController(controller) {
      if (!controller || typeof controller.abort !== "function") {
        return controller;
      }
      if (destroyed) {
        controller.abort();
        return controller;
      }
      abortControllers.add(controller);
      return controller;
    },
    own(resource) {
      if (!resource) return resource;
      const dispose = typeof resource === "function"
        ? resource
        : typeof resource.destroy === "function"
          ? () => resource.destroy()
          : typeof resource.dispose === "function"
            ? () => resource.dispose()
            : null;
      if (!dispose) return resource;
      if (destroyed) {
        dispose();
        return resource;
      }
      disposers.push(dispose);
      return resource;
    },
    trackNode(node) {
      if (!node || typeof node.remove !== "function") {
        return node;
      }
      if (destroyed) {
        node.remove();
        return node;
      }
      ownedNodes.add(node);
      return node;
    },
    destroy(...timerMaps) {
      if (destroyed) return;
      destroyed = true;
      abortControllers.forEach((controller) => controller.abort());
      abortControllers.clear();
      timers.forEach((timer) => {
        clearTimeout(timer);
        clearInterval(timer);
      });
      timers.clear();
      for (const timerMap of timerMaps) {
        for (const timer of timerMap.values()) clearTimeout(timer);
        timerMap.clear();
      }
      ownedNodes.forEach((node) => node.remove());
      ownedNodes.clear();
      disposers.splice(0).reverse().forEach((dispose) => dispose());
    },
  };
}
