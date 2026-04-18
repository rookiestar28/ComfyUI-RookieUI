# RookieUI Vite Feasibility Spike

This spike is intentionally non-production.

## Goal
- Answer whether the current RookieUI frontend graph can be built and previewed through a Vite path without changing the shipped ComfyUI extension entrypoints.

## Boundaries
- No production runtime import path is replaced.
- No shipped `web/*.js` entrypoint is rewritten for Vite.
- Any compatibility shim must stay inside `spikes/vite/`.

## Compatibility shim used by this spike
- `main.js` preloads `web/rookieui.css` and inserts a `#rookieui-styles` sentinel so the shipped extension entry does not inject a second runtime-only stylesheet URL during the preview.
- This proves a Vite-served harness path is possible, but also records that the current shipped stylesheet-injection model is not bundler-native by default.

## Decision gate
- `npm run spike:vite` must:
  - build successfully,
  - preview successfully,
  - mount the RookieUI sidebar shell in a browser,
  - leave production paths unchanged.

If any of those fail, the default-path decision remains deferred.

## Current outcome on 2026-04-18
- `build`: pass
- `preview runtime`: defer
- Objective blocker:
  - revisioned dynamic imports such as `assets/rookieui_api.js?v=...` are requested at runtime, but the Vite output emits hashed chunks instead of preserving the raw revisioned module filenames expected by `importRevisionedModule(...)`
- Decision:
  - keep the spike artifacts for future evaluation
  - do not switch the shipped RookieUI frontend to a Vite-served default path yet
