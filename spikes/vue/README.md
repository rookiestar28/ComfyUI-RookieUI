# Vue Host-Adapter Spike

## Purpose
- Prove that RookieUI can mount a bounded Vue sidebar extension against the same bootstrap contract already used by the shipped custom-render shell.
- Keep the current production entrypoint unchanged.

## Scope
- Uses the real `loadRookieUIBootstrapData(...)` composition seam with injected fixture loaders.
- Simulates the ComfyUI host extension slot contract with both:
  - `type: "custom"`
  - `type: "vue"`
- Verifies custom mount/unmount lifecycle still behaves while the Vue tab renders family-aware bootstrap metadata.

## Decision Snapshot
- Date: 2026-04-18
- Result: `keep-exploring`
- Evidence:
  - `npm run spike:vue`
  - `powershell -File scripts/run_full_tests_windows.ps1`
- Summary:
  - The Vue tab mounted cleanly.
  - The custom tab still mounted and unmounted cleanly in the same host-adapter proof.
  - The spike reused the real RookieUI bootstrap composition seam through injected loaders, so the proof was contract-based rather than a fake isolated demo.
- Acceptance rule:
  - `keep-exploring` if the Vue tab mounts cleanly, the custom tab still mounts/unmounts cleanly, and no runtime console/page errors occur.
  - `defer` if the adapter requires production-loader rewrites or fails to coexist with the current bootstrap contract.
