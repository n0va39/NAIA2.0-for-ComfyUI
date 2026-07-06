from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import sys
from typing import Any

EXTENSION_DIR = Path(__file__).resolve().parent
if str(EXTENSION_DIR) not in sys.path:
    sys.path.insert(0, str(EXTENSION_DIR))

from naia2_for_comfyui.aio_graph import (
    AIO_GENERATOR_NODE_ID,
    DEFAULT_MODEL_PARAMS,
    build_prompt_from_naia_params,
)


DEFAULT_SETTINGS = {
    "enabled": True,
    "auto_override": True,
    "allow_workflow_overwrite": False,
    "unet_name": DEFAULT_MODEL_PARAMS["unet_name"],
    "vae_name": DEFAULT_MODEL_PARAMS["vae_name"],
    "clip_name": DEFAULT_MODEL_PARAMS["clip_name"],
    "clip_type": DEFAULT_MODEL_PARAMS["clip_type"],
    "save_enabled": True,
    "filename_prefix": "NAIA2.0/Anima_AiO",
}

CLIP_TYPES = ["qwen_image", "stable_diffusion", "sdxl", "sd3", "flux"]

SCALAR_PARAM_KEYS = (
    "input",
    "negative_prompt",
    "width",
    "height",
    "resolution",
    "seed",
    "steps",
    "cfg",
    "cfg_scale",
    "sampler",
    "sampler_name",
    "scheduler",
    "denoise",
    "model",
    "unet_name",
    "vae_name",
    "clip_name",
    "clip_type",
    "save_enabled",
    "filename_prefix",
)


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


def _clean_text(value: Any, default: str = "") -> str:
    text = str(value if value is not None else default).strip()
    return text or default


def _load_settings(ctx: Any) -> dict[str, Any]:
    loader = getattr(ctx, "load_settings", None)
    try:
        raw = loader(DEFAULT_SETTINGS) if callable(loader) else dict(DEFAULT_SETTINGS)
    except Exception:
        raw = dict(DEFAULT_SETTINGS)
    raw = raw if isinstance(raw, Mapping) else {}
    settings = dict(DEFAULT_SETTINGS)
    settings.update(raw)
    settings["enabled"] = _as_bool(settings.get("enabled"), True)
    settings["auto_override"] = _as_bool(settings.get("auto_override"), True)
    settings["allow_workflow_overwrite"] = _as_bool(
        settings.get("allow_workflow_overwrite"),
        False,
    )
    settings["save_enabled"] = _as_bool(settings.get("save_enabled"), True)
    for key in ("unet_name", "vae_name", "clip_name", "clip_type", "filename_prefix"):
        settings[key] = _clean_text(settings.get(key), str(DEFAULT_SETTINGS[key]))
    return settings


def _panel_fields() -> list[dict[str, Any]]:
    return [
        {
            "key": "enabled",
            "type": "bool",
            "label": "Use AiO workflow",
            "default": DEFAULT_SETTINGS["enabled"],
            "section": "Run",
            "order": 10,
            "help": "Build a generated EasyUse Anima AiO graph from current NAIA params.",
        },
        {
            "key": "auto_override",
            "type": "bool",
            "label": "Override normal Generate",
            "default": DEFAULT_SETTINGS["auto_override"],
            "section": "Run",
            "order": 20,
            "help": "When COMFYUI mode dispatches a normal request, replace it with an AiO graph request.",
        },
        {
            "key": "allow_workflow_overwrite",
            "type": "bool",
            "label": "Overwrite loaded workflow",
            "default": DEFAULT_SETTINGS["allow_workflow_overwrite"],
            "section": "Run",
            "order": 30,
            "help": "Allow AiO generation even when NAIA already has a custom ComfyUI workflow loaded.",
        },
        {
            "key": "generate_now",
            "type": "action",
            "label": "Generate AiO now",
            "section": "Run",
            "order": 40,
            "help": "Queue one AiO generation from the current NAIA prompt and params.",
        },
        {
            "key": "unet_name",
            "type": "text",
            "label": "UNET",
            "default": DEFAULT_SETTINGS["unet_name"],
            "section": "Models",
            "order": 100,
        },
        {
            "key": "vae_name",
            "type": "text",
            "label": "VAE",
            "default": DEFAULT_SETTINGS["vae_name"],
            "section": "Models",
            "order": 110,
        },
        {
            "key": "clip_name",
            "type": "text",
            "label": "CLIP",
            "default": DEFAULT_SETTINGS["clip_name"],
            "section": "Models",
            "order": 120,
        },
        {
            "key": "clip_type",
            "type": "select",
            "label": "CLIP type",
            "options": CLIP_TYPES,
            "default": DEFAULT_SETTINGS["clip_type"],
            "section": "Models",
            "order": 130,
        },
        {
            "key": "save_enabled",
            "type": "bool",
            "label": "Save image",
            "default": DEFAULT_SETTINGS["save_enabled"],
            "section": "Output",
            "order": 200,
        },
        {
            "key": "filename_prefix",
            "type": "text",
            "label": "Filename prefix",
            "default": DEFAULT_SETTINGS["filename_prefix"],
            "section": "Output",
            "order": 210,
        },
    ]


class EasyUseAnimaAioExtension:
    def __init__(self, ctx: Any):
        self.ctx = ctx

    def register_panel(self) -> None:
        registrar = getattr(self.ctx, "register_panel", None)
        if callable(registrar):
            registrar(
                _panel_fields(),
                title="EasyUse Anima AiO",
                on_action=self.on_action,
            )

    def on_action(self, key: Any) -> None:
        if str(key or "") == "generate_now":
            self.generate_now()

    def generate_now(self) -> None:
        getter = getattr(self.ctx, "get_current_request", None)
        if not callable(getter):
            self._toast("Current request snapshot is not supported by this NAIA runtime.", "error")
            return
        snapshot = getter()
        if not isinstance(snapshot, Mapping) or not snapshot.get("ok"):
            self._toast(str((snapshot or {}).get("message") or "Could not read current request."), "error")
            return
        api_mode = str(snapshot.get("api_mode") or "").strip().upper()
        if api_mode != "COMFYUI":
            self._toast("EasyUse Anima AiO is available only in COMFYUI mode.", "warning")
            return
        params = snapshot.get("params") if isinstance(snapshot.get("params"), Mapping) else {}
        result = self._enqueue_aio(
            params,
            prompt_run_id=str(snapshot.get("prompt_run_id") or ""),
            priority=0,
        )
        if result.get("ok"):
            self._toast("EasyUse Anima AiO generation queued.", "success")
        else:
            self._toast(str(result.get("message") or "EasyUse Anima AiO queue failed."), "error")

    def on_generation_dispatched(self, info: Any) -> None:
        if not isinstance(info, Mapping):
            return
        if str(info.get("api_mode") or "").strip().upper() != "COMFYUI":
            return
        if str(info.get("ext_origin") or ""):
            return
        settings = _load_settings(self.ctx)
        if not settings["enabled"] or not settings["auto_override"]:
            return
        params = info.get("params") if isinstance(info.get("params"), Mapping) else {}
        if self._has_existing_workflow(params) and not settings["allow_workflow_overwrite"]:
            self._toast(
                "A custom ComfyUI workflow is already loaded. Enable overwrite in the AiO extension to replace it.",
                "warning",
            )
            return
        request_id = str(info.get("request_id") or info.get("generation_request_id") or "").strip()
        if not request_id:
            return
        cancel = self._cancel_original(request_id)
        if not (cancel.get("ok") or cancel.get("skip_scheduled")):
            self._toast(str(cancel.get("message") or "Could not cancel original generation."), "error")
            return
        result = self._enqueue_aio(
            params,
            prompt_run_id=str(info.get("prompt_run_id") or ""),
            priority=int(info.get("priority") or 0),
        )
        if not result.get("ok"):
            self._toast(str(result.get("message") or "EasyUse Anima AiO queue failed."), "error")

    def _enqueue_aio(
        self,
        params: Mapping[str, Any],
        *,
        prompt_run_id: str = "",
        priority: int = 0,
    ) -> dict[str, Any]:
        enqueue = getattr(self.ctx, "enqueue_generation", None)
        if not callable(enqueue):
            return {"ok": False, "message": "enqueue_generation is not supported by this NAIA runtime."}

        settings = _load_settings(self.ctx)
        merged = self._merge_params(params, settings)
        workflow = build_prompt_from_naia_params(merged)
        overrides = self._build_overrides(merged, workflow)
        try:
            return enqueue(
                overrides=overrides,
                prompt=str(merged.get("input") or merged.get("prompt") or ""),
                negative_prompt=str(merged.get("negative_prompt") or ""),
                api_mode="COMFYUI",
                prompt_run_id=prompt_run_id,
                priority=priority,
            )
        except Exception as exc:
            return {"ok": False, "message": str(exc)}

    def _merge_params(self, params: Mapping[str, Any], settings: Mapping[str, Any]) -> dict[str, Any]:
        merged = dict(params or {})
        merged["unet_name"] = _clean_text(settings.get("unet_name"), DEFAULT_SETTINGS["unet_name"])
        merged["vae_name"] = _clean_text(settings.get("vae_name"), DEFAULT_SETTINGS["vae_name"])
        merged["clip_name"] = _clean_text(settings.get("clip_name"), DEFAULT_SETTINGS["clip_name"])
        merged["clip_type"] = _clean_text(settings.get("clip_type"), DEFAULT_SETTINGS["clip_type"])
        merged["save_enabled"] = _as_bool(settings.get("save_enabled"), True)
        merged["filename_prefix"] = _clean_text(settings.get("filename_prefix"), DEFAULT_SETTINGS["filename_prefix"])
        return merged

    @staticmethod
    def _build_overrides(params: Mapping[str, Any], workflow: dict[str, Any]) -> dict[str, Any]:
        overrides = {
            "workflow": workflow,
            "_comfyui_output_node_id": AIO_GENERATOR_NODE_ID,
            "_remote_queue_label": "EasyUse Anima AiO",
            "easyuse_anima_aio_enabled": True,
        }
        for key in SCALAR_PARAM_KEYS:
            if key in params:
                overrides[key] = params[key]
        return overrides

    def _cancel_original(self, request_id: str) -> dict[str, Any]:
        cancel = getattr(self.ctx, "cancel_generation", None)
        if not callable(cancel):
            return {"ok": False, "message": "cancel_generation is not supported by this NAIA runtime."}
        try:
            return cancel(request_id)
        except Exception as exc:
            return {"ok": False, "message": str(exc)}

    @staticmethod
    def _has_existing_workflow(params: Mapping[str, Any]) -> bool:
        if not isinstance(params, Mapping):
            return False
        return bool(
            params.get("workflow")
            or params.get("comfyui_workflow")
            or params.get("comfyui_workflow_has_custom")
        )

    def _toast(self, message: str, level: str = "info") -> None:
        notifier = getattr(self.ctx, "show_toast", None)
        if callable(notifier):
            notifier(message, level)
            return
        logger = getattr(self.ctx, "log", None)
        if callable(logger):
            logger(f"{level}: {message}")


def register(ctx: Any) -> None:
    ext = EasyUseAnimaAioExtension(ctx)
    subscriber = getattr(ctx, "subscribe", None)
    if callable(subscriber):
        subscriber("generation_request_dispatched", ext.on_generation_dispatched)
    ext.register_panel()
