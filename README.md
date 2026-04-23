# ComfyUI-RookieUI
<br>

<div align="center">
  <img src="assets/rookieui.gif" width="100%" />
</div>

<br>

ComfyUI-RookieUI is a ComfyUI custom node extension that reproduces an A1111-style sidebar workflow while keeping inference inside native ComfyUI execution. **The project target is not only visual similarity.** RookieUI aims to reproduce A1111-style workflow semantics for Stable Diffusion in a ComfyUI host:

- **prompt / negative prompt parsing and conditioning behavior**
- **sampler / scheduler / seed / CFG mapping**
- **img2img, inpaint, and extras postprocessing flows**
- **integrated ControlNet and ADetailer behavior**
- **PNG metadata round-trip and apply workflow**
- **Prompt Workbench authoring tools and XYZ Plot sweep sessions**
- **queue / progress / result UX and host-integrated workflow behavior**

<br>

The core objective of this project is not merely to replicate the classic UI/UX, but to faithfully reproduce A1111's unique prompt parsing capabilities and image generation characteristics for the Stable Diffusion model family to the greatest extent possible. Even so, RookieUI supports more than just the Stable Diffusion family.

<details><summary><h2>Last Update - Click to expand</h2></summary>

<details>

<summary><strong>Official image-edit workflow expansion (new functionality/stability)</strong></summary>

- RookieUI now treats official image-edit workflows as `img2img`-owned image-edit subtypes instead of routing them through a dedicated visible `Edit` mode or a legacy SD-style inpaint fallback.
- The shipped first-wave official image-edit matrix now includes `Qwen-Image Edit`, `Qwen-Image Edit Multi-LoRA`, `FireRed Image Edit`, `FireRed Image Edit Lightning`, `Flux.1 Kontext Dev Edit`, `Flux.2 Image Edit`, `Flux.2 Klein 9B KV Image Edit`, and `Longcat Image Edit`.
- The separate visible `Qwen-Image Edit Multi-LoRA` `Img2Img` preset is now retired; keep using `Qwen-Image Edit` with prompt-inline multi-`<lora:...>` chaining while the backend compatibility profile remains available for truthful runtime compatibility.
- Image-edit flows now follow bounded official semantics directly in RookieUI: they do not require user masks, preserve ordered `reference_images` plus `main_reference_index`, and support bounded multi-reference input where the official template family requires it.

</details>

<details>

<summary><strong>Non-SD official template inline LoRA chaining (new functionality/stability)</strong></summary>

- RookieUI now supports prompt-inline `<lora:model_name:weight>` chaining on shipped official non-SD template workflows instead of limiting those families to hidden template defaults only.
- When an official non-SD preset already owns a template LoRA, RookieUI keeps the official default first and appends user prompt-inline LoRAs after it so the submitted ComfyUI graph matches the intended chained `Load LoRA` model path.
- The shipped non-SD inline LoRA path applies model-only LoRA nodes; when a prompt requests distinct clip/text-encoder strength, RookieUI now reports truthful drift messaging and uses the model-side strength only.

</details>

<details>

<summary><strong>Official img2img/edit flow split and template-owned LoRA truthfulness (new functionality/stability)</strong></summary>

- Split RookieUI's image-input workspace into truthful flow-aware surfaces: generic `img2img` now hides unaligned official non-SD presets, while shipped official edit workflows use dedicated image-edit handling on the shared `img2img` surface instead of falling back to the legacy SD-style i2i graph.
- RookieUI's image-input workspace now keeps generic SD-family `img2img` modes and official image-edit profiles on one truthful `img2img` surface, while still hiding unaligned official non-SD presets so they cannot fall back into the legacy SD-style i2i graph.
- Added the first shipped official edit preset, `Qwen-Image Edit`, following the official ComfyUI `imageEdit` template as a no-mask image-edit workflow rather than an inpaint-first surface.
- Official templates that preload a fixed LoRA are now exposed as template-owned defaults instead of silent hidden dependencies: RookieUI explicitly shows the official default, allows override with parity-drift messaging, and validates host readiness against the official LoRA asset.
- The current shipped template-owned LoRA handling applies to `Flux.1 Dev FP8`, `Qwen-Image 2512`, and `Qwen-Image Edit`.

</details>

<details>

<summary><strong>Official non-SD template preset expansion, inline LoRA chaining, and truthful host gating (new functionality/stability)</strong></summary>

- Expanded RookieUI's non-SD preset matrix to the official ComfyUI text-to-image templates currently tracked in `reference/workflow_templates`, including `Anima`, `Chroma`, `ERNIE-Image`, `ERNIE-Image Turbo`, `Flux.1 Dev FP8`, `Flux.2 Klein` variants, `HiDream i1` variants, `Longcat BF16`, `Qwen-Image 2512`, `Z-Image`, and `Z-Image Turbo`.
- Aligned runtime translation to official non-SD topology and parameter semantics instead of generic fallback graphs, including family-specific `Shift`, `Flux Guidance`, `Prompt Enhancement`, and template-owned hidden encoder bundles where the official workflows require them.
- Shipped official non-SD template paths now also support prompt-inline `<lora:model_name:weight>` chaining, preserving any template-owned LoRA first and then appending user inline LoRAs through model-only `Load LoRA` nodes before host submission.
- Tightened catalog validation so official non-SD presets only pass when the active ComfyUI host exposes the required family-aligned models and template assets; missing host assets are now reported as external prerequisites instead of silently accepted fallback matches.

</details>

<details>

<summary><strong>Prompt Workbench Danbooru host-action integration (new functionality/stability)</strong></summary>

- Added a truthful `Upsample Tags` editor-toolbar action to `Prompt Workbench`, backed by a dedicated RookieUI `/rookieui/prompt-tools/upsample` route and host-node detection against the active ComfyUI registry.
- The new action applies returned prompt text back into the active `Prompt Workbench` draft and bound prompt input without changing existing translation, AI-assist, history/favorites, or formatting behavior.
- When the host-side Danbooru upsampler node is missing or unavailable, RookieUI now reports explicit disabled-state and route-level `host-unavailable` behavior instead of implying the action is always present.
</details>

<details>

<summary><strong>Stateful-surface durability and runtime freshness hardening (stability/tooling)</strong></summary>

- Hardened `Prompt Workbench` and `XYZ Plot` persisted state with atomic JSON writes and corrupt-state quarantine instead of silent reset-on-parse-failure behavior.
- Added `XYZ Plot` async session-state coordination and bounded stale-session pruning so long-running hosts keep queue-backed sweep state consistent without unbounded retained history.

</details>

<details>

<summary><strong>Prompt Workbench and XYZ Plot delivery (new functionality/stability)</strong></summary>

- Shipped an integrated `Prompt Workbench` in the `txt2img` and `img2img` prompt band, with persisted prompt/negative namespaces, quick-insert catalogs, translation tooling, AI assist delivery, history/favorites, and blacklist-aware formatting.
- Shipped a built-in `XYZ Plot` sweep surface for `txt2img` and `img2img`, including axis registry, estimate checks, queue-backed session runs, main-grid/sub-grid assembly, primary-preview synchronization, fullscreen result inspection, and metadata-aware result delivery.
- Added recent `XYZ Plot` parity follow-ups for choice-axis multiselect entry, running partial-grid preview delivery, A1111-style seed-policy controls (`Keep -1 for seeds` plus per-axis seed variation toggles), and output mirroring for assembled grids.

</details>

<details>

<summary><strong>Extensibility refactor and architecture hardening (stability/maintainability)</strong></summary>

- Extracted shared workflow graph builders into `rookieui/services/workflow_builders/*`, keeping `workflow_translation.py` as the stable orchestration façade instead of a regrowing graph monolith.
- Split `ControlNet` and `ADetailer` backend ownership into focused catalog, normalization, runtime/refinement, and warning modules behind stable route-facing façades.
- Added backend/frontend integrated feature registries so sidebar bootstrap ownership no longer depends on ad-hoc one-off wiring.
- Added manifest-backed architecture guardrails, import-cycle checks, and façade size budgets to keep the refactor honest as these high-churn surfaces continue to expand.

**Architecture**

```text
ComfyUI process (single runtime)
|
+- ComfyUI core
|  +- native routes (/prompt, /history, /view, /ws, ...)
|  +- execution engine and model runtime
|
+- ComfyUI-RookieUI custom node package
   +- frontend sidebar shell + bootstrap registry
   |  +- web/rookieui_extension.js
   |  +- web/rookieui_feature_registry.js
   |  +- web/rookieui_sidebar_shell.js
   |
   +- internal routes under /rookieui/*
   +- stable backend facades
   |  +- workflow_translation.py
   |  +- controlnet.py
   |  +- adetailer.py
   |
   +- extracted backend ownership seams
   |  +- workflow_builders/*
   |  +- controlnet_* modules
   |  +- adetailer_* modules
   |  +- integrated_feature_registry.py
   |
   +- workflow submission into host ComfyUI queue
```

Current extension seams:

- `workflow_translation.py` is now a stable orchestration facade that delegates graph-building work into `rookieui/services/workflow_builders/*`.
- `controlnet.py` and `adetailer.py` stay as route-facing facades while catalog, normalization, runtime/refinement, and warning ownership live in focused vertical modules.
- `web/rookieui_extension.js` and `web/rookieui_feature_registry.js` now own integrated bootstrap loading explicitly, instead of scattering one-off feature fetch wiring through the extension entrypoint.
- The refactor is guarded by manifest-backed boundary checks, facade size budgets, and import-cycle regression coverage.

</details>

<details>

<summary><strong>SD-family prompt parity maximal continuation and host validation (new functionality/stability)</strong></summary>

- Added inventory-aware embeddings / textual inversion handling on the shipped SD-family prompt path, with canonical host-compatible `embedding:<name>` tokens and explicit missing-reference diagnostics.
- Added A1111-style alternate prompt scheduling for forms such as `[a|b]`, while keeping `BREAK`, `AND`, scheduling slices, and attention markers on RookieUI-owned SD-family encoder seams.
- Hardened SD-family token chunk behavior with recent comma backtrack and grouped textual-inversion boundary preservation when the active host tokenizer exposes word-id metadata, with safe fallback on hosts that do not.
- Added shared golden fixtures and reference-backed token differential coverage for the shipped SD-family parity surface.

</details>

<details>

<summary><strong>Native ADetailer and advanced ControlNet runtime upgrade (new functionality)</strong></summary>

- Upgraded ADetailer to a RookieUI-owned detector/runtime path with packaged Ultralytics/OpenCV-backed dependency support instead of relying on an external A1111 script or third-party node pack.
- Added native advanced ControlNet execution support for stage-aware weights, timestep scheduling, and mask-aware application in the shared RookieUI workflow translator.
- Kept main-generation ControlNet and ADetailer-local ControlNet on the same native apply seam so advanced behavior stays consistent across base and refinement stages.
- Improved runtime availability metadata so the UI can report the real detector/advanced-ControlNet capability surface instead of implying unsupported host features.

</details>

<details>

<summary><strong>Preview fullscreen viewer and frontend regression hardening (new functionality/stability)</strong></summary>

- Added a preview-only fullscreen viewer for generated images in `txt2img` and `img2img`, with direct surface activation and zoom-only inspection.
- Improved preview discoverability with visible overlay controls and consistent fullscreen enter/exit feedback.
- Hardened frontend regression coverage so fullscreen behavior is validated through real user actions instead of DOM-existence checks only.
- Added a shipped-frontend asset revision fingerprint guard to reduce stale-browser-cache regressions after UI hotfixes.

</details>

<details>

<summary><strong>ADetailer integrated parity rollout (new functionality)</strong></summary>

- Added an integrated ADetailer editor in `txt2img` and `img2img` with four unit tabs, grouped controls, and A1111-style layout on top of RookieUI's native sidebar shell.
- Added host-native detect-mask-refine workflow translation so enabled ADetailer units run as a secondary refinement stage without embedding A1111 ScriptRunner runtime.
- Added ControlNet `none` / `passthrough` / `custom` behavior inside the ADetailer refinement context, keeping base-generation ControlNet state isolated from detailer-local execution.
- Added detector/model availability guidance, warning codes, and diagnostics so degraded ADetailer behavior is reported explicitly instead of silently disappearing.
- Added route-level regression coverage and rollback/no-op validation for the full ADetailer runtime chain.

</details>

<details>

<summary><strong>Stable Diffusion prompt parity rollout (new functionality)</strong></summary>

- Added RookieUI-owned A1111-style prompt compilation for the Stable Diffusion family, including support for `BREAK`, `AND`, scheduling slices, and attention markers.
- Added SD-family parity text-encode routing so prompt semantics compile into deterministic ComfyUI conditioning graphs instead of relying on raw prompt passthrough.
- Kept newer/non-SD families on their native ComfyUI text-encode/runtime paths, aligning the product scope to A1111 reproduction where it is actually meaningful.
- Added capability and API truthfulness updates so the UI reports the real prompt-semantics support surface instead of implying unsupported parity on unrelated model families.

</details>

<details>

<summary><strong>ControlNet preprocessor execution and diagnostics hardening (bugfix/stability)</strong></summary>

- Added control-type-aware preprocessor option narrowing, so each type shows only relevant annotator choices.
- Expanded preprocessor catalog to include variant-level options (for example depth/lineart/openpose families) in integrated ControlNet units.
- Updated backend detect/runtime dispatch to respect selected preprocessor variants, prefer matching host annotator nodes, and keep OpenPose-family execution isolated to the requested variant instead of cross-family fallback synthesis.
- Improved run-preprocessor status messaging to report both the selected preprocessor option and the actual backend processor used, with explicit warning diagnostics when the host output is degraded or unavailable.
- Expanded backend/frontend regression coverage for variant filtering and variant-aware dispatch behavior.

</details>

<details>

<summary><strong>Diffusion-family decode integrity and selector hardening (bugfix/stability)</strong></summary>

- Fixed a diffusion-family decode mismatch path where sampler preview could look normal but final output degraded due to incompatible fallback VAE pairing.
- Enforced family-specific selector resolution for diffusion-model profiles so `vae_name` and `text_encoder_name` no longer rely on a global default fallback.
- Added fail-fast normalization checks for unresolved diffusion-family selectors to surface configuration problems before workflow translation/runtime execution.
- Expanded regression coverage across Flux, Qwen-Image, Klein, Lumina, ZiT, Wan, and Anima selector/normalization matrices.

</details>

<details>

<summary><strong>ControlNet A1111-native parity (new functionality)</strong></summary>

- Added A1111-style multi-unit ControlNet editing surface in generation panes (`txt2img` and `img2img`).
- Added host-native ControlNet graph integration for `txt2img`, `img2img`, and `inpaint`, with deterministic multi-unit apply order.
- Added dual payload compatibility for RookieUI-native units and A1111-style `alwayson_scripts.controlnet` input.
- Added canonical `/rookieui/controlnet/*` routes and A1111-compatible `/controlnet/*` alias routes.
- Added optional preprocessor/detect downgrade behavior with explicit warning diagnostics when optional dependencies are unavailable.

</details>

<details>

<summary><strong>Runtime contract and UX consistency fixes (bugfix/stability)</strong></summary>

- Updated shell version display to use backend capability payload sourced from `pyproject.toml`, removing hardcoded frontend version coupling.
- Fixed `RookieUILoadAssetMask` validation signature mismatch that could raise missing-argument errors during img2img inpaint validation.
- Fixed mask-canvas slider consistency issue where `Opacity` / `Zoom` initial displayed values and slider positions could diverge.
- Expanded targeted regression coverage for the above runtime and UI-state contract paths.

</details>

<details>

<summary><strong>Prompt semantics parity (new functionality)</strong></summary>

- Added structured prompt-semantic parsing for `AND`, `BREAK`, scheduling slices, and attention markers.
- Added conditioning-plan compilation so parsed prompt semantics map into ComfyUI conditioning graph composition for txt2img and img2img flows.
- Preserved deterministic inline LoRA extraction/merge behavior while expanding prompt semantics support.

</details>

<details>

<summary><strong>Parity guardrails and rollout safety (stability)</strong></summary>

- Added stable warning-code diagnostics for prompt parsing/compilation paths.
- Added a bounded legacy fallback switch so prompt-semantics rollout can be reverted safely in runtime variance scenarios.
- Expanded regression checks around parser/compiler integration and fallback behavior.

</details>

<details>

<summary><strong>Img2Img source/mask handoff hardening (bugfix)</strong></summary>

- Fixed a mask-canvas placeholder false-positive where `No source image` could appear after a valid txt2img `Send to Img2Img` handoff.
- Hardened source-binding visibility contract for mask-canvas preview so source image state and placeholder state remain consistent.
- Added regression coverage for source-image/mask bridge behavior in send-to-img2img flow.

</details>

<details>

<summary><strong>Extras Hires recovery and secondary family preset expansion</strong></summary>

- Restored a visible A1111-style `Hires. fix` section in Extras, including collapsible chrome and a functional `Enable Hires` toggle wired to the real upscale execution path.
- Reorganized Extras upscale controls into the recovered Hires section so the UI surface matches active backend behavior instead of acting as decorative duplicates.
- Expanded secondary preset/profile lanes with new family entries: `Klein (Flux.2)`, `Lumina`, `ZiT (Z-Image-Turbo)`, `Wan`, and `Anima`.
- Updated model-family catalog mapping and compatibility listings so the new secondary families resolve consistently in the shared RookieUI payload surfaces.

</details>

<details>

<summary><strong>Img2Img workflow expansion and interaction polish</strong></summary>

- Added an embedded Img2Img in-app mask canvas with core controls: brush/eraser, size/opacity, undo/redo, clear/invert, zoom/pan/fit, and explicit `Apply Mask`.
- Added advanced mask editing operations for inpaint usability: rectangle selection, selection fill/erase/invert, and bounded selection move controls.
- Introduced a dedicated Img2Img mode router contract so visible mode switching and backend mode payload stay synchronized through one deterministic path.
- Upgraded Img2Img mode UX to A1111-style second-level generation subtabs (`img2img`, `Sketch`, `Inpaint`, `Inpaint sketch`, `Inpaint upload`, `Batch`) while preserving existing backend compatibility.
- Hardened high-risk UI paths with focused regression coverage and reran full backend/frontend validation gates after each stage.

</details>
</details>

## Table of Contents

- [Last Update](#last-update---click-to-expand)
- [Installation](#installation)
- [Feature Overview](#feature-overview)
  - [Official Non-SD Template Presets](#official-non-sd-template-presets)
  - [Image-Edit Workflows](#image-edit-workflows)
  - [Current Official Image-Edit Coverage and Template-Owned LoRAs](#current-official-image-edit-coverage-and-template-owned-loras)
  - [Official Non-SD Inline LoRA Support](#official-non-sd-inline-lora-support)
- [Extensions](#extensions)
  - [Prompt Workbench](#prompt-workbench)
    - [Prompt Workbench Danbooru Upsampler Action](#prompt-workbench-danbooru-upsampler-action)
  - [XYZ Plot](#xyz-plot)
  - [ControlNet Support](#controlnet-support)
  - [ADetailer Support](#adetailer-support)
  - [Support for Other Extensions](#support-for-other-extensions)
- [Runtime and Host Integration](#runtime-and-host-integration)
  - [Stable Diffusion Prompt Parity](#stable-diffusion-prompt-parity)
  - [Default Model Read Paths](#default-model-read-paths-host-comfyui)
- [License](#license)


## Installation

1. Install via ComfyUI-Manager (recommended)
   Update ComfyUI-Manager to the latest version first, then search for `ComfyUI-RookieUI` in Manager and install it.
   RookieUI now ships a root `requirements.txt` so Manager-style installs can resolve the extension's extra Python dependencies in the host environment.

2. Install as a ComfyUI custom node (manual)

```bash
git clone https://github.com/rookiestar28/ComfyUI-RookieUI custom_nodes/ComfyUI-RookieUI
cd custom_nodes/ComfyUI-RookieUI
python -m pip install -r requirements.txt
```

Then restart ComfyUI. The `RookieUI` sidebar tab will be available in the frontend host.

`ControlNet` and `ADetailer` support are built into RookieUI itself. You do not need to install separate external custom-node packs just to use RookieUI's integrated ControlNet or ADetailer surfaces.

Required extra Python packages for RookieUI:

- `opencv-python-headless>=4.10.0`
- `ultralytics>=8.3.0`

If your host or Manager install path does not automatically install custom-node dependencies, run `python -m pip install -r requirements.txt` manually in the same Python environment used by ComfyUI. These packages power RookieUI's native ADetailer detector/runtime path and related image-processing helpers.

## Feature Overview

### Sidebar UI

<div align="left">
  <img src="assets/rookiesidebar.png" width="80%" />
</div>
<br>

- A1111-like compact tab rail and control panel layout
- Hero `Generate` rail with compact action icons
- Family-aware preset behavior with SD-family parity lanes plus official non-SD template-backed preset/profile lanes
- Progress text and queue/history integration in sidebar flow
- Live preview panel with runtime updates and flicker-mitigated rendering
- Fullscreen preview viewer for generated results, with direct surface activation and zoom-only inspection

### Generation

- `txt2img` request normalization and workflow translation
- `img2img` request normalization with guarded asset-handle path
- `img2img` mode surface: `img2img`, `sketch`, `inpaint`, `inpaint_sketch`, `inpaint_upload`, `batch`
- Hires second-pass controls for generation flows (`txt2img` and `img2img`)
- Stable Diffusion family prompt semantics parity for `BREAK`, `AND`, scheduling slices, alternate scheduling, attention markers, and embeddings / textual inversion tokens
- Official non-SD template translation for shipped txt2img presets, including family-specific parameter mapping such as `shift`, `flux_guidance`, and `prompt_enhancement_enabled` where the official workflow requires them
- ComfyUI-native prompt submission with RookieUI origin metadata

### Image-Edit Workflows

<br>
<div align="left">
  <img src="assets/edit.png" width="100%" />
</div>
<br>

- official image-edit workflows now live on the `img2img` surface as dedicated image-edit profiles instead of a separate visible `Edit` mode
- shipped first-wave image-edit profiles: `Qwen-Image Edit`, `Qwen-Image Edit Multi-LoRA`, `FireRed Image Edit`, `FireRed Image Edit Lightning`, `Flux.1 Kontext Dev Edit`, `Flux.2 Image Edit`, `Flux.2 Klein 9B KV Image Edit`, and `Longcat Image Edit`
- `Qwen-Image Edit Multi-LoRA` remains backend/runtime-compatible, but the separate visible `Img2Img` preset is retired; the canonical UI path is `Qwen-Image Edit` plus prompt-inline multi-`<lora:...>` chaining
- image-edit request normalization preserves ordered `reference_images` and `main_reference_index` so official single-reference and bounded multi-reference workflows can share one truthful payload surface
- image-edit flows do not require user masks; mask-oriented SD inpaint controls stay on the normal `img2img` inpaint paths instead of leaking into official edit workflows
- family-specific edit builders now cover template-owned LoRA chaining, Qwen/Qwen+ edit encoders, Flux/Klein multi-reference latent setup, and Longcat edit guidance on dedicated non-SD runtime paths

### Prompt Workbench

- integrated prompt-band workbench in `txt2img` and `img2img`
- persisted `prompt` / `negative` namespace state, history, and favorites
- quick-insert catalogs for group tags, prompt-library entries, embeddings, and LoRA references
- translation, prompt analysis, AI assist delivery, and blacklist-aware formatting tools
- truthful Danbooru host-action support for `Upsample Tags` when the host-side upsampler node is installed and available
- provider truthfulness for shipped, deferred, reference-only, and misconfigured Prompt Workbench provider states

### XYZ Plot

- integrated bottom-mounted sweep surface in `txt2img` and `img2img`
- axis registry with estimate checks before queue submission and multiselect choice-axis entry where appropriate
- queue-backed session runs with progress, cancellation, seed-policy controls, and result tracking
- running sessions can surface partial main-grid preview while completed results sync into the shared preview box and the normal host output flow
- delivered results include main grid, sub-grids, lone cell images, fullscreen inspection support, and XYZ metadata

### PNG Info

- image-first metadata ingest
- A1111 metadata parsing path
- automatic positive/negative prompt extraction
- apply parsed parameters into `txt2img` or `img2img`
- ComfyUI metadata remains inspect-only, while A1111 inpaint metadata surfaces explicit `missing_inputs` diagnostics until the required mask/source assets are selected manually

### Extras

- single-image/batch postprocessing surface
- dedicated extras contract and execution path
- truthful guarded warning behavior for face-restoration requests that are not yet executed inside RookieUI's workspace-local pipeline

### ADetailer

- integrated multi-unit ADetailer surface in `txt2img` and `img2img`
- four-unit editor with grouped controls and override gating
- host-native detect-mask-refine runtime chain
- RookieUI-native detector/runtime path backed by packaged Python dependencies instead of an external ADetailer node pack
- ControlNet `none` / `passthrough` / `custom` support inside detailer refinement
- explicit diagnostics and availability guidance for degraded detector/model states

### Model Controls

- SD1.5, SDXL, Pony, Illustrious, and Noob use RookieUI's Stable Diffusion parity text-encode path for A1111-style prompt semantics and inventory-aware embeddings / textual inversion handling
- Official non-SD template presets now surface family-specific controls only when the upstream workflow exposes them, including `Shift`, `Flux Guidance`, and `Prompt Enhancement`
- Fixed template-owned encoder bundles keep `Text Encoder` controls hidden on the shipped official non-SD preset matrix instead of implying a user-selectable pairing that the official template does not expose
- Clip Skip remains editable in UI; some profiles may ignore it at execution time

### Official Non-SD Template Presets

- RookieUI now ships official ComfyUI template-backed txt2img presets for `Anima`, `Chroma`, `ERNIE-Image`, `ERNIE-Image Turbo`, `Flux.1 Dev FP8`, `Flux.2 4B Distilled Klein`, `Flux.2 4B Klein`, `Flux.2 9B Distilled Klein`, `Flux.2 9B Klein`, `HiDream i1 Dev FP8`, `HiDream i1 fast`, `HiDream i1 full`, `Longcat BF16`, `Qwen-Image 2512`, `Z-Image`, and `Z-Image Turbo`.
- These presets follow official template defaults for width, height, steps, CFG, sampler, and scheduler, and they keep template-owned encoder bundles hidden when the official workflow hard-codes those pairings.
- Family-specific controls are now preserved where the official workflows require them:
  - `Shift`: `Chroma`, `HiDream i1 Dev FP8`, `HiDream i1 fast`, `HiDream i1 full`, `Qwen-Image 2512`, `Z-Image`, `Z-Image Turbo`
  - `Flux Guidance`: `Longcat BF16`
  - `Prompt Enhancement`: `ERNIE-Image`, `ERNIE-Image Turbo`
- Official `Edit` workflows now ship as `img2img` image-edit profiles on the shared `Img2Img` preset surface rather than a separate visible `Edit` UI. `Flux.2 Dev`, whose official graph includes `LoadImage` / `VAEEncode`, remains classified outside the current txt2img preset rollout.

### Current Official Image-Edit Coverage and Template-Owned LoRAs

- RookieUI now ships first-wave official ComfyUI `imageEdit` coverage for `Qwen-Image Edit`, `Qwen-Image Edit Multi-LoRA`, `FireRed Image Edit`, `FireRed Image Edit Lightning`, `Flux.1 Kontext Dev Edit`, `Flux.2 Image Edit`, `Flux.2 Klein 9B KV Image Edit`, and `Longcat Image Edit`.
- The `Qwen-Image Edit Multi-LoRA` backend profile remains shipped for compatibility, but RookieUI no longer exposes it as a separate visible `Img2Img` preset because prompt-inline multi-`<lora:...>` chaining is the canonical UI path.
- Official edit workflows are treated as image-edit flows, not as mask-first inpaint surfaces. The shipped image-edit path does not require mask input.
- Multi-reference image-edit families now use canonical ordered `reference_images` plus `main_reference_index` payloads on the shared `img2img` request surface, with bounded first-wave support for official multi-reference templates such as `FireRed Image Edit`, `Flux.1 Kontext Dev Edit`, and `Flux.2 Klein 9B KV Image Edit`.
- Generic `img2img` now hides official non-SD presets that are not yet aligned to an official image-input runtime, so users cannot accidentally route them into the legacy SD-style i2i graph and assume template parity that does not exist.
- Official templates that preload a fixed LoRA are treated as template-owned dependencies rather than silent hidden assets:
  - RookieUI shows the official default explicitly
  - allows manual override
  - and warns when a custom override no longer matches the official ComfyUI template exactly
- The current shipped template-owned LoRA pattern applies to:
  - `Flux.1 Dev FP8`
  - `Qwen-Image 2512`
  - `Qwen-Image Edit`
  - `Qwen-Image Edit Multi-LoRA`
  - `FireRed Image Edit Lightning`
- Other official image-edit presets may still remain host prerequisites on a given environment until the exact upstream model, text encoder, VAE, and template-owned LoRA labels required by the official template are installed on that host.

---

### Official Non-SD Inline LoRA Support

<div align="left">
  <img src="assets/loras.png" width="100%" />
</div>

<br>

- Shipped official non-SD template workflows now accept prompt-inline LoRA syntax such as `<lora:model_name:1>` on their native template runtime path instead of treating inline LoRAs as Stable Diffusion-only behavior.
- RookieUI extracts inline LoRA activations from the prompt, creates model-only `Load LoRA` nodes, and chains them immediately after the official `Load Diffusion Model` path before submitting the final ComfyUI workflow JSON to the host.
- When a preset already owns an official template LoRA, RookieUI preserves the official default first and appends prompt-inline LoRAs after it. This means the effective order is:
  - `Load Diffusion Model`
  - template-owned `Load LoRA` nodes
  - prompt-inline `Load LoRA` nodes
- This support is intended for shipped official non-SD template txt2img/edit builders such as the current `Flux.1 Dev FP8`, `Qwen-Image 2512`, and `Qwen-Image Edit` paths.

Simple usage:

1. Select a shipped official non-SD preset.
2. Type prompt-inline LoRA syntax directly in the prompt, for example `<lora:example_model:1>`.
3. Generate normally; RookieUI will append the corresponding model-only `Load LoRA` nodes automatically before the host run.

Behavior and limits:

- On non-SD official templates, inline LoRAs are currently treated as model-only LoRAs.
- If the prompt requests different model-side and clip/text-encoder-side strengths, RookieUI warns about parity drift and applies the model-side strength only.
- Template-owned official defaults remain the source of truth for official-template parity. Adding extra inline LoRAs is treated as extending the official template, not as strict unchanged parity.

### Model Support

- Stable Diffusion family
- Official non-SD template preset families: `Anima`, `Chroma`, `ERNIE-Image`, `Flux.1` / `Flux.2 Klein`, `HiDream i1`, `Longcat Image`, `Qwen-Image`, and `Z-Image`
- `Z-Image` also covers the current Lumina/Z-Image naming lineage used by the official host templates and RookieUI aliases

Prompt semantics note:

- Exact A1111-style prompt parsing and conditioning parity is currently targeted at the Stable Diffusion family.
- Newer/non-SD families continue to use their native ComfyUI execution semantics even when exposed in the same RookieUI interface.

## Extensions

### Prompt Workbench

<div align="left">
  <img src="assets/prompt_workbench.png" width="70%" />
</div>

<br>

Simple usage:

1. Open `txt2img` or `img2img`, then click `Open Workbench` in the prompt band.
2. Switch between the `Prompt` and `Negative` scopes depending on which field you want to edit, then use `Capture Current Text` if you want to pull the current field value into the workbench explicitly.
3. Use the `Editor`, `History`, `Favorites`, `Catalog`, `Assist`, and `Format` panels as needed; token insertion, formatting cleanup, blacklist application, translation, and AI assist all operate on the active scope.
4. Choose a configured shipped translation or AI-assist provider before running translation/assist actions, then apply the returned text back into the active RookieUI prompt field.
5. Use `Upsample Tags` when you want the active prompt expanded through the host-installed Danbooru upsampler node; the returned text writes back into the current Prompt Workbench draft and prompt field.
6. Insert, rewrite, or clean prompt text; the active scope writes back to the current RookieUI prompt field and persists across refreshes.

Behavior and compatibility:

- `Prompt Workbench` is built directly into RookieUI's prompt band instead of relying on an A1111 textarea hijack or a separate external extension surface.
- State is persisted separately for the shipped `txt2img` / `img2img` prompt and negative namespaces.
- Catalog surfaces expose group tags, prompt-library entries, embeddings, and LoRA quick-insert helpers on the same workbench seam.
- Translation and AI-assist delivery run through the built-in `/rookieui/prompt-tools/*` route family, with explicit truthfulness when a provider is shipped but unconfigured, deferred, reference-only, or otherwise unavailable on the current host/setup.
- The current shipped translation execution paths are OpenAI-compatible chat translation and MyMemory public translation; AI assist currently uses the OpenAI-compatible provider contract.

#### Prompt Workbench Danbooru Upsampler Action

Simple usage:

1. Install the host-side `ComfyUI-Danbooru-Tags-Upsampler` node in the same ComfyUI environment as RookieUI, then restart ComfyUI so the node is visible in the active host registry.
2. Open `txt2img` or `img2img`, click `Open Workbench`, and stay on the primary `Prompt` scope.
3. Prepare the current prompt text, then click `Upsample Tags`.
4. RookieUI sends the current prompt through the host Danbooru upsampler route and applies the returned text back into the active workbench draft and bound prompt field.

Behavior and compatibility:

- `Upsample Tags` is a host action, not a translation provider or AI-assist provider.
- The action is currently limited to the primary `Prompt` scope; it is intentionally disabled on the `Negative` scope.
- RookieUI only enables the action when the active ComfyUI host exposes a compatible Danbooru upsampler node alias.
- If the host node is missing or unavailable, the toolbar remains truthful through disabled-state messaging and the backend route returns explicit `host-unavailable` status instead of pretending the feature exists.

---

### XYZ Plot

<div align="center">
  <img src="assets/xyzplot.gif" width="90%" />
</div>

<br>

Simple usage:

1. Open `txt2img` or `img2img`, scroll below `Hires.fix`, `ADetailer`, and `ControlNet`, then expand `XYZ Plot`.
2. Start from the current form as the base request, choose the `X`, `Y`, and optional `Z` axis types, then enter the values to sweep. Choice-backed axes use the built-in multiselect dropdown, while free-text axes still accept manual value entry.
3. Review the seed controls when your sweep depends on deterministic or coordinate-varying seeds. RookieUI now supports `Keep -1 for seeds` plus separate `Vary seeds for X/Y/Z` toggles.
4. Run an estimate first to review generated image count, session warnings, and whether the current axis combination can execute.
5. Start the session and watch the session panel for progress. Running sessions can surface partial main-grid preview before the final assembled result is ready.
6. Inspect the generated main grid, sub-grids, or lone cell images when the run completes; assembled grids also mirror into the shared preview lane and normal host output flow.

Behavior and compatibility:

- `XYZ Plot` is integrated into RookieUI instead of being exposed as an A1111 script runner, but it stays as a dedicated bottom-mounted sweep surface in the generation panes.
- The surface is intentionally mounted below the `ADetailer` and `ControlNet` blocks and now follows the same collapsed-by-default section behavior as the surrounding extension panels.
- Runs are queue-backed sessions rather than a single monolithic prompt submission, so RookieUI can track per-session progress, cancellation, seed materialization, and grid assembly explicitly.
- Choice-backed axes use a RookieUI-owned multiselect dropdown with fill/clear behavior instead of forcing CSV-only entry for every choice axis.
- The current shipped seed-policy surface includes `Keep -1 for seeds`, per-axis `Vary seeds for X/Y/Z` toggles, and truthful fixed-seed/session metadata.
- Delivered results include a main grid, optional sub-grids, lone cell images, attached XYZ metadata for later inspection/reuse, and fullscreen zoom inspection through the shared preview viewer.

---

### ControlNet Support

<div align="left">
  <img src="assets/controlnet.png" width="80%" />
</div>
<br>

Simple usage:

1. Open `txt2img` or `img2img`, then enable a `ControlNet Unit`.
2. Upload a source image for that unit.
3. Choose a `Control Type`; the `Preprocessor` dropdown is automatically filtered to matching options.
4. Select a `Preprocessor` and (optionally) a `Model`, then click `Run Preprocessor` to update the preview lane.
5. Keep `Allow Preview` enabled if you want to display preprocessor output side-by-side.
6. Run generation. The ControlNet model is applied at generation stage, while preprocessor preview comes from the selected annotator/preprocessor.

Behavior and compatibility:

- A1111-style multi-unit ControlNet editor is available in `txt2img` and `img2img`.
- Backend execution uses native ComfyUI ControlNet nodes with deterministic multi-unit apply order.
- RookieUI ships its own integrated ControlNet request/runtime layer, so the feature does not depend on installing a separate external ControlNet UI extension.
- Selected preprocessor variants are dispatched to matching host annotator nodes when available, including exact OpenPose-family variant routing.
- Advanced native ControlNet behavior is available through RookieUI's shared runtime seam, including staged weighting, timestep scheduling, and mask-aware application where supported by the selected route.
- Request compatibility supports both RookieUI native units and A1111-style `alwayson_scripts.controlnet` payloads.
- API surface provides both canonical RookieUI routes and A1111-compatible aliases:
  - `/rookieui/controlnet/*`
  - `/controlnet/*`
- ControlNet still requires host-side ControlNet model files; when a requested host preprocessor/runtime capability is unavailable, RookieUI returns explicit warning diagnostics and fallback status.

---

### ADetailer Support

<div align="left">
  <img src="assets/adetailer.png" width="40%" />
</div>
<br>

Simple usage:

1. Open `txt2img` or `img2img`, then enable `ADetailer`.
2. Pick an enabled ADetailer unit and select a detector.
3. Adjust prompt, negative prompt, mask, inpaint, and refinement overrides as needed.
4. Optionally choose ADetailer-local ControlNet mode: `none`, `passthrough`, or `custom`.
5. Run generation. Enabled ADetailer units refine the base result in a host-native secondary pass.

Behavior and compatibility:

- The ADetailer surface is integrated directly into RookieUI's generation panes instead of relying on an external A1111 script runner.
- Runtime behavior follows a detect-mask-refine pipeline built from native ComfyUI/RookieUI workflow nodes.
- Detector/runtime support is packaged with RookieUI's own dependency/runtime layer; no separate external ADetailer custom-node pack is required.
- Up to four ADetailer units are supported in the integrated editor.
- ControlNet coupling supports `none`, `passthrough`, and `custom` modes inside the refinement context.
- Native detector runtime uses RookieUI's packaged Python dependencies together with host model inventory, so matching detector/model files must still exist in the host environment.
- Availability guidance and warning diagnostics are exposed when detector/model/runtime dependencies are degraded.

### Support for Other Extensions

- Additional extension-style surfaces beyond the currently shipped `ControlNet`, `ADetailer`, `Prompt Workbench`, and `XYZ Plot` tooling will be added incrementally.

---

## Runtime and Host Integration

### Stable Diffusion Prompt Parity

RookieUI's strongest A1111-style parity claims are intentionally limited to the Stable Diffusion family. On these profiles, prompt execution is routed through RookieUI-owned encoder nodes instead of relying on raw stock `CLIPTextEncode*` passthrough.

Current shipped SD-family parity surface:

- `BREAK`
- `AND` / weighted multi-condition composition
- scheduling slices such as `[from:to:at]`
- alternate prompt scheduling such as `[a|b]`
- attention markers such as `(text:1.2)`, `(text)`, and `[text]`
- inventory-aware embeddings / textual inversion tokens on the shipped prompt path

Runtime and validation notes:

- `SD1.5`, `SDXL`, `Pony`, `Illustrious`, and `Noob` use the same RookieUI parity text-encode seam.
- Token chunk rebatching applies recent comma backtrack and preserves grouped textual-inversion boundaries when the active host tokenizer exposes word-id metadata; hosts without that metadata fall back safely to the baseline tokenize path.
- The shipped parity surface is backed by golden parser/translator fixtures and reference-backed differential coverage.
- Newer/non-SD families remain available in RookieUI, but they continue to use native ComfyUI prompt/runtime semantics instead of claiming A1111 parity.

Other official non-SD or image-edit presets may remain unavailable on a given host until the required diffusion model, encoder bundle, VAE, template-owned LoRA, or other official template asset is installed in that specific ComfyUI environment. RookieUI now treats those as host prerequisites instead of silently claiming fallback parity.

### Default Model Read Paths (Host ComfyUI)

RookieUI reads model catalogs from the host ComfyUI `folder_paths` keys. Under standard ComfyUI defaults, paths are:

- Checkpoints: `<ComfyUI>/models/checkpoints`
- Text Encoders (`text_encoders`): `<ComfyUI>/models/text_encoders`, `<ComfyUI>/models/clip`
- CLIP (`clip`, legacy alias): `<ComfyUI>/models/text_encoders`, `<ComfyUI>/models/clip`
- Diffusion Models (`diffusion_models`): `<ComfyUI>/models/unet`, `<ComfyUI>/models/diffusion_models`
- UNet (`unet`, legacy alias): `<ComfyUI>/models/unet`, `<ComfyUI>/models/diffusion_models`
- VAE: `<ComfyUI>/models/vae`
- LoRA: `<ComfyUI>/models/loras`
- Embeddings: `<ComfyUI>/models/embeddings`
- CLIP Vision: `<ComfyUI>/models/clip_vision`
- Upscale Models: `<ComfyUI>/models/upscale_models`
- ControlNet: `<ComfyUI>/models/controlnet`, `<ComfyUI>/models/t2i_adapter`
- Ultralytics: host `folder_paths`-defined location (commonly `<ComfyUI>/models/ultralytics` on hosts that provide this key)


## License

This project is licensed under **GNU Affero General Public License v3.0 (AGPL-3.0)**.

See [LICENSE](LICENSE).
