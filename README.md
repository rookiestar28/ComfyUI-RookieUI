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

The core objective of this project is not merely to replicate the classic UI/UX, but to faithfully reproduce A1111's unique prompt parsing capabilities and image generation characteristics for the Stable Diffusion model family to the greatest extent possible. Newer model families remain available in the same RookieUI surface, but they continue to use their native ComfyUI execution semantics instead of claiming exact A1111 prompt parity.

<details><summary><h2>Last Update - Click to expand</h2></summary>

<details>

<summary><strong>ADetailer integrated parity rollout (new functionality)</strong></summary>

- Added an integrated ADetailer editor in `txt2img` and `img2img` with four unit tabs, grouped controls, and Forge/A1111-style layout on top of RookieUI's native sidebar shell.
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

- Added Forge-style preprocessor option narrowing by selected Control Type, so each type shows only relevant annotator choices.
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
- [Architecture Snapshot](#architecture-snapshot)
- [Installation](#installation)
- [Feature Overview](#feature-overview)
- [Default Model Read Paths](#default-model-read-paths-host-comfyui)
- [ControlNet Support](#controlnet-support)
- [ADetailer Support](#adetailer-support)
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
- Stable Diffusion family prompt semantics parity for `BREAK`, `AND`, scheduling slices, and attention markers
- ComfyUI-native prompt submission with RookieUI origin metadata

### PNG Info

- image-first metadata ingest
- A1111 metadata parsing path
- automatic positive/negative prompt extraction
- apply parsed parameters into `txt2img` or `img2img`

### Extras

- single-image/batch postprocessing surface
- dedicated extras contract and execution path

### ADetailer

- integrated multi-unit ADetailer surface in `txt2img` and `img2img`
- four-unit editor with grouped controls and override gating
- host-native detect-mask-refine runtime chain
- ControlNet `none` / `passthrough` / `custom` support inside detailer refinement
- explicit diagnostics and availability guidance for degraded detector/model states

### Model Controls

- SD1.5/SDXL use RookieUI's Stable Diffusion parity text-encode path for A1111-style prompt semantics
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

Prompt semantics note:

- Exact A1111-style prompt parsing and conditioning parity is currently targeted at the Stable Diffusion family.
- Newer/non-SD families continue to use their native ComfyUI execution semantics even when exposed in the same RookieUI interface.

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
- Selected preprocessor variants are dispatched to matching host annotator nodes when available, including exact OpenPose-family variant routing.
- Request compatibility supports both RookieUI native units and A1111-style `alwayson_scripts.controlnet` payloads.
- API surface provides both canonical RookieUI routes and A1111-compatible aliases:
  - `/rookieui/controlnet/*`
  - `/controlnet/*`
- When a host preprocessor is unavailable, RookieUI returns explicit warning diagnostics and fallback status.

## ADetailer Support

Simple usage:

1. Open `txt2img` or `img2img`, then enable `ADetailer`.
2. Pick an enabled ADetailer unit and select a detector.
3. Adjust prompt, negative prompt, mask, inpaint, and refinement overrides as needed.
4. Optionally choose ADetailer-local ControlNet mode: `none`, `passthrough`, or `custom`.
5. Run generation. Enabled ADetailer units refine the base result in a host-native secondary pass.

Behavior and compatibility:

- The ADetailer surface is integrated directly into RookieUI's generation panes instead of relying on an external A1111 script runner.
- Runtime behavior follows a detect-mask-refine pipeline built from native ComfyUI/RookieUI workflow nodes.
- Up to four ADetailer units are supported in the integrated editor.
- ControlNet coupling supports `none`, `passthrough`, and `custom` modes inside the refinement context.
- Availability guidance and warning diagnostics are exposed when detector/model/runtime dependencies are degraded.

## Support for Other Extensions

- Additional extension features beyond ControlNet will be added incrementally.


## License

This project is licensed under **GNU Affero General Public License v3.0 (AGPL-3.0)**.

See [LICENSE](LICENSE).
