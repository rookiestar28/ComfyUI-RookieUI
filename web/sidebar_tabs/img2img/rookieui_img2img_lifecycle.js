export function createImg2ImgLifecycle() {
  let destroyed = false;
  let epoch = 0;
  const disposers = [];
  const timers = new Set();
  const abortControllers = new Set();
  const ownedNodes = new Set();
  const trackedObjectUrls = new Map();

  const removeDisposer = (disposer) => {
    const index = disposers.indexOf(disposer);
    if (index >= 0) disposers.splice(index, 1);
  };

  const addDisposer = (dispose) => {
    if (typeof dispose !== "function") return () => {};
    if (destroyed) {
      dispose();
      return () => {};
    }
    disposers.push(dispose);
    return () => {
      removeDisposer(dispose);
      dispose();
    };
  };

  return {
    get destroyed() {
      return destroyed;
    },
    listen(target, eventName, handler, options) {
      if (destroyed || !target?.addEventListener || typeof handler !== "function") return () => {};
      target.addEventListener(eventName, handler, options);
      return addDisposer(() => target.removeEventListener?.(eventName, handler, options));
    },
    timeout(callback, delay = 0) {
      if (destroyed || typeof callback !== "function") return null;
      const timer = setTimeout(() => {
        timers.delete(timer);
        if (!destroyed) callback();
      }, delay);
      timers.add(timer);
      return timer;
    },
    interval(callback, delay = 0) {
      if (destroyed || typeof callback !== "function") return null;
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
      if (!controller || typeof controller.abort !== "function") return controller;
      if (destroyed) {
        controller.abort();
        return controller;
      }
      abortControllers.add(controller);
      return controller;
    },
    trackObjectUrl(url, revoke = globalThis.URL?.revokeObjectURL) {
      const normalizedUrl = String(url ?? "").trim();
      if (!normalizedUrl || typeof revoke !== "function") return normalizedUrl;
      if (destroyed) {
        revoke(normalizedUrl);
        return normalizedUrl;
      }
      if (!trackedObjectUrls.has(normalizedUrl)) {
        trackedObjectUrls.set(normalizedUrl, revoke);
        addDisposer(() => {
          const disposer = trackedObjectUrls.get(normalizedUrl);
          if (!disposer) return;
          trackedObjectUrls.delete(normalizedUrl);
          disposer(normalizedUrl);
        });
      }
      return normalizedUrl;
    },
    own(resource) {
      if (!resource) return resource;
      const dispose = typeof resource === "function"
        ? resource
        : typeof resource.destroy === "function"
          ? () => {
              resource.destroy();
              resource.unmount?.();
            }
          : typeof resource.dispose === "function"
            ? () => resource.dispose()
            : typeof resource.unmount === "function"
              ? () => resource.unmount()
              : null;
      if (dispose) addDisposer(dispose);
      return resource;
    },
    trackNode(node) {
      if (!node || typeof node.remove !== "function") return node;
      if (destroyed) {
        node.remove();
        return node;
      }
      ownedNodes.add(node);
      return node;
    },
    beginAsyncEpoch() {
      epoch += 1;
      return epoch;
    },
    invalidateAsyncEpoch() {
      epoch += 1;
      return epoch;
    },
    isAsyncEpochCurrent(candidate) {
      return !destroyed && Number.isInteger(candidate) && candidate === epoch;
    },
    destroy(...timerMaps) {
      if (destroyed) return;
      destroyed = true;
      epoch += 1;
      abortControllers.forEach((controller) => controller.abort());
      abortControllers.clear();
      timers.forEach((timer) => {
        clearTimeout(timer);
        clearInterval(timer);
      });
      timers.clear();
      for (const timerMap of timerMaps) {
        if (!timerMap?.values) continue;
        for (const timer of timerMap.values()) {
          clearTimeout(timer);
          clearInterval(timer);
        }
        timerMap.clear?.();
      }
      ownedNodes.forEach((node) => node.remove());
      ownedNodes.clear();
      disposers.splice(0).reverse().forEach((dispose) => dispose());
      trackedObjectUrls.clear();
    },
  };
}
