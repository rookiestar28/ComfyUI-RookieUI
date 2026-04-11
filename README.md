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
- [Feature Overview](#feature-overview)
- [Default Model Read Paths](#default-model-read-paths-host-comfyui)
- [ControlNet Support](#controlnet-support)
- [Installation](#installation)
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

- SD1.5/SDXL use model-native text-encoder behavior
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

- A1111-style multi-unit ControlNet editor is available in `txt2img` and `img2img` generation panes.
- Backend execution uses native ComfyUI ControlNet nodes with deterministic multi-unit apply order.
- Request compatibility supports both RookieUI native units and A1111-style `alwayson_scripts.controlnet` payloads.
- API surface provides both canonical RookieUI routes and A1111-compatible aliases:
  - `/rookieui/controlnet/*`
  - `/controlnet/*`
- Optional preprocessor/detect dependency is handled with explicit downgrade diagnostics when unavailable.

## Installation

Install as a ComfyUI custom node:

```bash
git clone https://github.com/rookiestar28/ComfyUI-RookieUI custom_nodes/ComfyUI-RookieUI
```

Then restart ComfyUI. The `RookieUI` sidebar tab will be available in the frontend host.


## License

This project is licensed under **GNU Affero General Public License v3.0 (AGPL-3.0)**.

See [LICENSE](LICENSE).
