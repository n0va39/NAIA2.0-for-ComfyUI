from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

PROMPT_STUDIO_NODE_ID = "1"
INPUT_NODE_ID = "2"
AIO_GENERATOR_NODE_ID = "3"

PROMPT_STUDIO_CLASS = "EasyUseAnimaPromptStudioAdvancedV2"
INPUT_CLASS = "EasyUseAnimaInput"
AIO_GENERATOR_CLASS = "EasyUseAnimaAIOGenerator"

PROMPT_DATA_TYPE = "EASYUSE_ANIMA_PROMPT_DATA"
EASY_USE_ANIMA_INPUT_TYPE = "EASY_USE_ANIMA_INPUT"

AIO_GENERATION_SCHEMA = "easyuse_anima_aio_generation_settings"
AIO_INPUT_SCHEMA = "easy_use_anima_input"

WILDCARD_MODE_FIXED_LABEL = "\uace0\uc815"
SEED_CONTROL_FIXED = "fixed"
MAX_SEED = 1125899906842624 - 1

DEFAULT_MODEL_PARAMS = {
    "unet_name": "ANIMA\\anima_baseV10.safetensors",
    "vae_name": "qwen_image_vae.safetensors",
    "clip_name": "qwen_3_06b_base.safetensors",
    "clip_type": "qwen_image",
}


def _first(params: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        value = params.get(key)
        if value is not None and value != "":
            return value
    return default


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        text = value.strip().casefold()
        if text in {"1", "true", "yes", "y", "on"}:
            return True
        if text in {"0", "false", "no", "n", "off"}:
            return False
    return bool(value)


def _as_int(
    value: Any,
    default: int,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        number = int(default)
    if minimum is not None:
        number = max(minimum, number)
    if maximum is not None:
        number = min(maximum, number)
    return number


def _as_float(
    value: Any,
    default: float,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = float(default)
    if minimum is not None:
        number = max(minimum, number)
    if maximum is not None:
        number = min(maximum, number)
    return number


def _snap_to_multiple(value: int, multiple: int = 32) -> int:
    return max(multiple, int(round(value / multiple) * multiple))


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def normalize_naia_params(params: Mapping[str, Any] | None) -> dict[str, Any]:
    source = dict(params or {})
    width = _snap_to_multiple(
        _as_int(_first(source, "width", "resolution_width", default=1024), 1024, minimum=32, maximum=8192)
    )
    height = _snap_to_multiple(
        _as_int(_first(source, "height", "resolution_height", default=1024), 1024, minimum=32, maximum=8192)
    )

    normalized = {
        "prompt": str(_first(source, "prompt", "positive", "positive_prompt", default="") or ""),
        "negative_prompt": str(_first(source, "negative_prompt", "negative", default="") or ""),
        "width": width,
        "height": height,
        "seed": _as_int(_first(source, "seed", default=0), 0, minimum=0, maximum=MAX_SEED),
        "seed_after_generate": str(_first(source, "seed_after_generate", default=SEED_CONTROL_FIXED) or SEED_CONTROL_FIXED),
        "steps": _as_int(_first(source, "steps", default=32), 32, minimum=1, maximum=1000),
        "cfg": _as_float(_first(source, "cfg", "cfg_scale", default=5.0), 5.0, minimum=0.0, maximum=100.0),
        "sampler_name": str(_first(source, "sampler_name", "sampler", default="er_sde") or "er_sde"),
        "scheduler": str(_first(source, "scheduler", default="simple") or "simple"),
        "denoise": _as_float(_first(source, "denoise", default=1.0), 1.0, minimum=0.0, maximum=1.0),
        "save_enabled": _as_bool(_first(source, "save_enabled", "save", default=True), True),
        "filename_prefix": str(_first(source, "filename_prefix", default="NAIA2.0/Anima_AiO") or "NAIA2.0/Anima_AiO"),
    }
    normalized.update({
        key: str(_first(source, key, default=value) or value)
        for key, value in DEFAULT_MODEL_PARAMS.items()
    })
    return normalized


def build_advanced_fields(params: Mapping[str, Any] | None) -> str:
    normalized = normalize_naia_params(params)
    fields = [
        {
            "id": "positive_naia",
            "pane": "positive",
            "type": "naia",
            "label": "NAIA Prompt",
            "text": normalized["prompt"],
            "height": 150,
            "enabled": True,
            "pin": False,
        },
        {
            "id": "negative_naia",
            "pane": "negative",
            "type": "naia",
            "label": "NAIA Negative Prompt",
            "text": normalized["negative_prompt"],
            "height": 120,
            "enabled": True,
            "pin": False,
        },
    ]
    return _json_dumps(fields)


def build_input_settings(options: Mapping[str, Any] | None = None) -> dict[str, Any]:
    options = dict(options or {})
    resources = dict(options.get("resources") or {})
    return {
        "schema": AIO_INPUT_SCHEMA,
        "version": 1,
        "resources": {
            "loader_mode": str(resources.get("loader_mode") or "split"),
            "clip_loader": str(resources.get("clip_loader") or "single"),
            "unet_weight_dtype": str(resources.get("unet_weight_dtype") or "default"),
            "clip_device": str(resources.get("clip_device") or "default"),
        },
        "metadata": {},
    }


def build_generation_settings(
    params: Mapping[str, Any] | None,
    options: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = normalize_naia_params(params)
    options = dict(options or {})
    save_backend = str(options.get("save_backend") or "comfy_save_image")
    return {
        "schema": AIO_GENERATION_SCHEMA,
        "version": 1,
        "mode": "txt2img",
        "sampler": {
            "backend": "comfy_ksampler",
            "seed": normalized["seed"],
            "seed_after_generate": normalized["seed_after_generate"],
            "steps": normalized["steps"],
            "cfg": normalized["cfg"],
            "sampler_name": normalized["sampler_name"],
            "scheduler": normalized["scheduler"],
            "denoise": normalized["denoise"],
            "spectrum": {"enabled": False},
            "dit_corrections": {"enabled": False},
        },
        "model_patches": {
            "dave": {"enabled": False},
            "safe_pag": {"enabled": False},
            "kj": {
                "fp16_accumulation": False,
                "sage_attention": "disabled",
                "sage_allow_compile": False,
                "torch_compile": {
                    "enabled": False,
                    "disable_dynamic_vram": True,
                },
            },
        },
        "artist_mix": {"mode": "off"},
        "highres": {"enabled": False},
        "detailer": {"enabled": False},
        "upscale": {"enabled": False},
        "postprocess": {"enabled": False},
        "save": {
            "enabled": normalized["save_enabled"],
            "backend": save_backend,
            "image_saver": {
                "filename": normalized["filename_prefix"],
                "path": "",
                "extension": "webp",
                "embed_workflow": True,
                "save_prompt_metadata": True,
                "download_civitai_data": False,
                "easy_remix": False,
            },
        },
        "preview": {
            "intermediate_images": False,
            "compare_previous": False,
            "image_feed": False,
            "feed_count": 12,
        },
    }


def build_prompt_studio_inputs(params: Mapping[str, Any] | None) -> dict[str, Any]:
    normalized = normalize_naia_params(params)
    return {
        "use_naia": False,
        "consume_naia_on_queue": False,
        "use_anima_mod_guidance": False,
        "resolution_bucket": "Custom",
        "resolution_size": f"{normalized['width']} * {normalized['height']}",
        "resolution_custom_width": normalized["width"],
        "resolution_custom_height": normalized["height"],
        "pin_trigger_tags_to_front": False,
        "advanced_fields": build_advanced_fields(normalized),
        "use_negative_anima_mod_guidance": False,
        "wildcard_mode": WILDCARD_MODE_FIXED_LABEL,
        "wildcard_seed": normalized["seed"],
        "wildcard_seed_after_generate": SEED_CONTROL_FIXED,
        "artist_mix_mode": "off",
        "artist_mix_start_percent": 0.5,
        "artist_mix_strength_scale": 1.0,
        "artist_mix_style_gain": 1.35,
        "artist_mix_rms_scale_cap": 2.0,
        "artist_mix_exact_top_k": 4,
        "artist_mix_cluster_count": 4,
        "artist_mix_dominant_isolation": True,
        "artist_mix_dominant_threshold": 0.25,
    }


def build_prompt_from_naia_params(
    params: Mapping[str, Any] | None,
    options: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = normalize_naia_params(params)
    options = dict(options or {})
    input_settings = build_input_settings(options.get("input_settings") if isinstance(options.get("input_settings"), Mapping) else None)
    generation_settings = build_generation_settings(normalized, options)

    return {
        PROMPT_STUDIO_NODE_ID: {
            "class_type": PROMPT_STUDIO_CLASS,
            "inputs": build_prompt_studio_inputs(normalized),
        },
        INPUT_NODE_ID: {
            "class_type": INPUT_CLASS,
            "inputs": {
                PROMPT_DATA_TYPE: [PROMPT_STUDIO_NODE_ID, 0],
                "unet_name": normalized["unet_name"],
                "vae_name": normalized["vae_name"],
                "clip_name": normalized["clip_name"],
                "clip_type": normalized["clip_type"],
                "input_settings": _json_dumps(input_settings),
            },
        },
        AIO_GENERATOR_NODE_ID: {
            "class_type": AIO_GENERATOR_CLASS,
            "inputs": {
                "easy_use_anima_input": [INPUT_NODE_ID, 0],
                "generation_settings": _json_dumps(generation_settings),
            },
        },
    }
