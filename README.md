# ComfyUI-RookieUI
<br>

<div align="center">
  <img src="assets/rookieui.gif" width="100%" />
</div>

<br>
<br>

ComfyUI-RookieUI is a ComfyUI custom node extension that reproduces an A1111/Forge-style sidebar workflow while keeping inference inside native ComfyUI execution. **The project target is not only visual similarity.** RookieUI aims to reproduce A1111-style **workflow semantics** for Stable Diffusion in a ComfyUI host:

- **prompt and negative prompt handling**
- **sampler/scheduler/seed/CFG behavior mapping**
- **img2img and extras postprocessing flows**
- **PNG metadata round-trip and apply workflow**
- **queue/progress/result UX that feels close to A1111 usage**

<br>

The core objective of this project is not merely to replicate the classic UI/UX, but to faithfully reproduce A1111's unique prompt parsing capabilities and image generation characteristics for the Stable Diffusion model family to the greatest extent possible. That being said, RookieUI's support extends far beyond just the SD models.

<details><summary><h2>Last Update - Click to expand</h2></summary>

<details>

<summary><strong>A1111-native prompt parity node delivery (new functionality)</strong></summary>

- Added RookieUI-owned A1111 parity text-encode nodes for SD-family default routes, moving `AND`, `BREAK`, scheduling, and attention handling to the CLIP/tokenizer boundary instead of relying on graph-only approximation.
- Added SD1.x / SD2.x parity-node execution for standard CLIP paths and SDXL dual-encoder parity-node execution with pooled-output/size metadata preservation.
- Added hires-pass prompt-conditioning separation for SDXL parity routes so second-pass scheduling and chunk timing no longer collapse back onto the base pass.
- Preserved rollback-safe legacy graph fallback behavior for environments that still need the older prompt path.

</details>

<details>

<summary><strong>Prompt capability and warning truthfulness realignment (bugfix/stability)</strong></summary>

- Updated backend/frontend capability payloads so default SD-family prompt behavior is reported as exact, while legacy fallback and secondary-family approximate lanes are surfaced explicitly.
- Added structured warning-code metadata for semantic detection, fallback, guardrails, and unsupported extra-network families.
- Corrected legacy warning copy so prompt-path downgrades clearly state when RookieUI is running the legacy graph fallback instead of the default parity-node route.
- Synced offline/frontend fallback capability payloads with the same post-cutover prompt contract to avoid contradictory UI messaging.

</details>

<details>

<summary><strong>ControlNet OpenPose and host-preprocessor execution hardening (bugfix/stability)</strong></summary>

- Fixed OpenPose-family host preprocessing so selected variants execute with exact host-node/flag binding instead of drifting into unrelated preprocessors.
- Removed the generic visual-empty rejection that incorrectly treated sparse pose outputs as failures, especially for OpenPose-family previews.
- Corrected fallback preview behavior so host failures no longer echo the source image as if preprocessing succeeded.
- Expanded schema-aware host parameter coercion and regression coverage for OpenPose-family and other variant-driven preprocessor paths.

</details>

<details>

<summary><strong>ControlNet preprocessor UX and dispatch parity improvements (bugfix/stability)</strong></summary>

- Added Forge-style preprocessor option narrowing by selected Control Type, so each type shows only relevant annotator choices.
- Expanded preprocessor catalog to include variant-level options (for example depth/lineart/openpose families) in integrated ControlNet units.
- Updated backend detect/runtime dispatch to respect selected preprocessor variants and prefer matching host annotator nodes.
- Improved run-preprocessor status messaging to report both selected preprocessor option and actual backend processor used.
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
- [Architecture Snapshot](#architecture-snapshot)
- [Installation](#installation)
- [Feature Overview](#feature-overview)
- [Prompt Semantics and A1111 Parity](#prompt-semantics-and-a1111-parity)
- [Default Model Read Paths](#default-model-read-paths-host-comfyui)
- [ControlNet Support](#controlnet-support)
- [Support for Other Extensions](#support-for-other-extensions)
- [License](#license)

## Architecture Snapshot

```text
ComfyUI process (single runtime)
|
+- ComfyUI core
|  +- native routes (/prompt, /history, /view, /ws, ...)
|  +- execution engine and model runtime
|
+- ComfyUI-RookieUI custom node package
   +- frontend sidebar shell (web/rookieui_sidebar_shell.js, web/rookieui.css)
   +- internal routes under /rookieui/*
   +- request normalization and parity translation services
   +- workflow submission into host ComfyUI queue
```

## Installation

1. Install via ComfyUI-Manager (recommended)
   Update ComfyUI-Manager to the latest version first, then search for `ComfyUI-RookieUI` in Manager and install it.

2. Install as a ComfyUI custom node (manual)

```bash
git clone https://github.com/rookiestar28/ComfyUI-RookieUI custom_nodes/ComfyUI-RookieUI
```

Then restart ComfyUI. The `RookieUI` sidebar tab will be available in the frontend host.

## Feature Overview

### Sidebar UI

<div align="left">
  <img src="assets/rookiesidebar.png" width="80%" />
</div>
<br>

- A1111/Forge-like compact tab rail and control panel layout
- Hero `Generate` rail with compact action icons
- Family-aware preset behavior (SD-family first) with Flux/Qwen preset lanes
- Progress text and queue/history integration in sidebar flow
- Live preview panel with runtime updates and flicker-mitigated rendering

### Generation

- `txt2img` request normalization and workflow translation
- `img2img` request normalization with guarded asset-handle path
- `img2img` mode surface: `img2img`, `sketch`, `inpaint`, `inpaint_sketch`, `inpaint_upload`, `batch`
- Hires second-pass controls for generation flows (`txt2img` and `img2img`)
- SD-family default prompt execution uses RookieUI A1111 parity text-encode nodes instead of graph-only prompt approximation
- Exact prompt support on default SD-family routes for `AND`, `BREAK`, scheduling, and attention weighting
- ComfyUI-native prompt submission with RookieUI origin metadata

### PNG Info

- image-first metadata ingest
- A1111 metadata parsing path
- automatic positive/negative prompt extraction
- apply parsed parameters into `txt2img` or `img2img`

### Extras

- single-image/batch postprocessing surface
- dedicated extras contract and execution path

### Model Controls

- SD1.5/SDXL default routes use RookieUI-owned A1111 parity text-encode nodes at the host CLIP boundary
- Flux and Qwen-Image expose selectable text encoder controls
- Clip Skip remains editable in UI; some profiles may ignore it at execution time

### Model Support

- Stable Diffusion family
- Flux family (expanded coverage)
- Qwen-Image family (expanded coverage)
- Wan family
- ZiT family
- Klein family
- Lumina family
- Anima family

## Prompt Semantics and A1111 Parity

- Default Stable Diffusion-family routes (`sd15`, `sdxl`, Pony, Illustrious, Noob) execute prompt semantics through RookieUI A1111 parity text-encode nodes.
- Supported default SD-family prompt features include:
  - `AND` composition
  - `BREAK` chunking
  - prompt scheduling syntax such as `[from:to:at]`
  - parenthesis/bracket attention weighting and explicit `(text:weight)` emphasis
  - inline LoRA / LyCORIS extraction into deterministic loader chains
- Secondary newer-family routes still exist, but they are not described as exact A1111 prompt-parity lanes in RookieUI capability surfaces.
- If you enable `ROOKIEUI_PROMPT_DSL_LEGACY`, RookieUI falls back to the older graph-based prompt path and reports that downgrade explicitly in warning diagnostics.

## Default Model Read Paths (Host ComfyUI)

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

## ControlNet Support

<div align="left">
  <img src="assets/controlnet.png" width="85%" />
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
- Preprocessor selection is Control Type-aware and preserves explicit variant choice for families such as depth, lineart, and OpenPose.
- OpenPose-family host preprocessing keeps exact selected variant semantics and avoids misleading source-image echo on fallback failure.
- Request compatibility supports both RookieUI native units and A1111-style `alwayson_scripts.controlnet` payloads.
- API surface provides both canonical RookieUI routes and A1111-compatible aliases:
  - `/rookieui/controlnet/*`
  - `/controlnet/*`
- When a host preprocessor is unavailable, RookieUI returns explicit warning diagnostics and fallback status.

## Support for Other Extensions

- Additional extension features beyond ControlNet will be added incrementally.


## License

This project is licensed under **GNU Affero General Public License v3.0 (AGPL-3.0)**.

See [LICENSE](LICENSE).
