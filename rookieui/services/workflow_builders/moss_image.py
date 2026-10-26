from __future__ import annotations

from rookieui.contracts.generation import NormalizedTxt2ImgRequest
from rookieui.services.moss_image import validate_moss_host
from rookieui.services.moss_layout import compile_moss_layout
from rookieui.services.workflow_builders.core import (
    NodeIdAllocator, _build_unet_loader_node, _build_clip_loader_node,
    _build_vae_loader_node, _build_sampler_node,
)
from rookieui.services.workflow_builders.output import _build_decode_and_save


def build_moss_image_workflow(request: NormalizedTxt2ImgRequest) -> dict[str, object]:
    options = request.moss_options
    if options is None:
        raise ValueError('MOSS requires normalized moss_options.')
    validate_moss_host(slg_enabled=options.slg_enabled, sampler=request.sampler_name, scheduler=request.scheduler_name)
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    model_id, clip_id, vae_id = (allocator.next() for _ in range(3))
    workflow[model_id] = _build_unet_loader_node(request.checkpoint_name)
    workflow[clip_id] = _build_clip_loader_node(request.text_encoder_name, clip_type='moss_image')
    workflow[vae_id] = _build_vae_loader_node(request.vae_name)
    model_source = [model_id, 0]
    if options.slg_enabled:
        slg_id = allocator.next()
        workflow[slg_id] = {'class_type': 'SkipLayerGuidanceDiTSimple', 'inputs': {
            'model': model_source, 'double_layers': '', 'single_layers': '22',
            'start_percent': 0.0, 'end_percent': 0.5,
        }}
        model_source = [slg_id, 0]
    conditioning = []
    positive_text = compile_moss_layout(request.prompt, options.layout, request.width, request.height)
    for text in (positive_text, request.negative_prompt):
        encode_id = allocator.next()
        workflow[encode_id] = {'class_type': 'CLIPTextEncode', 'inputs': {'clip': [clip_id, 0], 'text': text}}
        conditioning.append(encode_id)
    latent_id = allocator.next()
    # CRITICAL: MOSS uses 128-channel /16 FLUX.2 latents. SD/Flux.1 empty latents
    # are incompatible; native MOSS owns shift 5, so do not add a sampling patch.
    workflow[latent_id] = {'class_type': 'EmptyFlux2LatentImage', 'inputs': {
        'width': request.width, 'height': request.height, 'batch_size': request.batch_size,
    }}
    sampler_id = allocator.next()
    _build_sampler_node(workflow, node_id=sampler_id, positive_id=conditioning[0], negative_id=conditioning[1],
                        latent_id=latent_id, request=request, denoise=1.0, model_source=model_source)
    _build_decode_and_save(workflow, sampler_id=sampler_id, decode_id=allocator.next(), save_id=allocator.next(),
                           vae_source=[vae_id, 0], request=request)
    return workflow
