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

### Planned Model Support

- Flux family (expanded coverage)
- Qwen-Image family (expanded coverage)
- Wan family
- ZiT family
- Klein family
- Lumina family
- Anima family

## Installation

Install as a ComfyUI custom node:

```bash
git clone https://github.com/rookiestar28/ComfyUI-RookieUI custom_nodes/ComfyUI-RookieUI
```

Then restart ComfyUI. The `RookieUI` sidebar tab will be available in the frontend host.


## License

This project is licensed under **GNU Affero General Public License v3.0 (AGPL-3.0)**.

See [LICENSE](LICENSE).
