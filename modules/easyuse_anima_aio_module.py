from __future__ import annotations

from typing import Any

from PyQt6.QtWidgets import QCheckBox, QComboBox, QFormLayout, QLineEdit, QVBoxLayout, QWidget

from interfaces.base_module import BaseMiddleModule
from interfaces.mode_aware_module import ModeAwareModule
from naia2_for_comfyui.aio_graph import build_prompt_from_naia_params
from ui.scaling_manager import get_scaled_size


class EasyUseAnimaAioModule(BaseMiddleModule, ModeAwareModule):
    """NAIA2.0 middle-section extension for generated EasyUse Anima AiO graphs."""

    def __init__(self):
        BaseMiddleModule.__init__(self)
        ModeAwareModule.__init__(self)
        self.NAI_compatibility = False
        self.WEBUI_compatibility = False
        self.COMFYUI_compatibility = True
        self.settings_base_filename = "easyuse_anima_aio"
        self.widget: QWidget | None = None
        self.enable_checkbox: QCheckBox | None = None
        self.unet_name_edit: QLineEdit | None = None
        self.vae_name_edit: QLineEdit | None = None
        self.clip_name_edit: QLineEdit | None = None
        self.clip_type_combo: QComboBox | None = None
        self.save_enabled_checkbox: QCheckBox | None = None
        self.filename_prefix_edit: QLineEdit | None = None

    def get_title(self) -> str:
        return "EasyUse Anima AiO"

    def get_module_name(self) -> str:
        return self.get_title()

    def get_order(self) -> int:
        return 38

    def initialize_with_context(self, context):
        self.app_context = context

    def on_initialize(self):
        self._install_workflow_builder_patch()

    def create_widget(self, parent) -> QWidget:
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(get_scaled_size(8), get_scaled_size(8), get_scaled_size(8), get_scaled_size(8))
        layout.setSpacing(get_scaled_size(8))

        self.enable_checkbox = QCheckBox("Use generated EasyUse Anima AiO graph")
        self.enable_checkbox.setChecked(False)
        layout.addWidget(self.enable_checkbox)

        form = QFormLayout()
        form.setSpacing(get_scaled_size(6))

        self.unet_name_edit = QLineEdit("ANIMA\\anima_baseV10.safetensors")
        self.vae_name_edit = QLineEdit("qwen_image_vae.safetensors")
        self.clip_name_edit = QLineEdit("qwen_3_06b_base.safetensors")
        self.clip_type_combo = QComboBox()
        self.clip_type_combo.addItems(["qwen_image", "stable_diffusion", "sdxl"])
        self.save_enabled_checkbox = QCheckBox()
        self.save_enabled_checkbox.setChecked(True)
        self.filename_prefix_edit = QLineEdit("NAIA2.0/Anima_AiO")

        form.addRow("UNET", self.unet_name_edit)
        form.addRow("VAE", self.vae_name_edit)
        form.addRow("CLIP", self.clip_name_edit)
        form.addRow("CLIP type", self.clip_type_combo)
        form.addRow("Save image", self.save_enabled_checkbox)
        form.addRow("Filename prefix", self.filename_prefix_edit)
        layout.addLayout(form)
        layout.addStretch(1)

        self.widget = widget
        return widget

    def collect_current_settings(self) -> dict[str, Any]:
        return {
            "enabled": bool(self.enable_checkbox and self.enable_checkbox.isChecked()),
            "unet_name": self._line_text(self.unet_name_edit),
            "vae_name": self._line_text(self.vae_name_edit),
            "clip_name": self._line_text(self.clip_name_edit),
            "clip_type": self.clip_type_combo.currentText() if self.clip_type_combo else "qwen_image",
            "save_enabled": bool(self.save_enabled_checkbox and self.save_enabled_checkbox.isChecked()),
            "filename_prefix": self._line_text(self.filename_prefix_edit),
        }

    def apply_settings(self, settings: dict[str, Any]):
        if not isinstance(settings, dict):
            return
        if self.enable_checkbox is not None:
            self.enable_checkbox.setChecked(bool(settings.get("enabled", False)))
        self._set_line_text(self.unet_name_edit, settings.get("unet_name"))
        self._set_line_text(self.vae_name_edit, settings.get("vae_name"))
        self._set_line_text(self.clip_name_edit, settings.get("clip_name"))
        self._set_line_text(self.filename_prefix_edit, settings.get("filename_prefix"))
        if self.save_enabled_checkbox is not None:
            self.save_enabled_checkbox.setChecked(bool(settings.get("save_enabled", True)))
        if self.clip_type_combo is not None and settings.get("clip_type"):
            text = str(settings["clip_type"])
            index = self.clip_type_combo.findText(text)
            if index < 0:
                self.clip_type_combo.addItem(text)
                index = self.clip_type_combo.findText(text)
            self.clip_type_combo.setCurrentIndex(index)

    def get_parameters(self) -> dict[str, Any]:
        if not self.enable_checkbox or not self.enable_checkbox.isChecked():
            return {}
        return {
            "workflow_type": "easyuse_anima_aio",
            "easyuse_anima_aio_enabled": True,
            "unet_name": self._line_text(self.unet_name_edit),
            "vae_name": self._line_text(self.vae_name_edit),
            "clip_name": self._line_text(self.clip_name_edit),
            "clip_type": self.clip_type_combo.currentText() if self.clip_type_combo else "qwen_image",
            "save_enabled": bool(self.save_enabled_checkbox and self.save_enabled_checkbox.isChecked()),
            "filename_prefix": self._line_text(self.filename_prefix_edit),
        }

    def _install_workflow_builder_patch(self):
        if self.app_context is None:
            return
        manager = getattr(self.app_context, "comfyui_workflow_manager", None)
        if manager is None or getattr(manager, "_easyuse_anima_aio_patch_installed", False):
            return

        original_apply = manager.apply_params_to_workflow

        def apply_params_to_workflow_with_easyuse_aio(params: dict[str, Any]):
            if isinstance(params, dict) and params.get("workflow_type") == "easyuse_anima_aio":
                return build_prompt_from_naia_params(params)
            return original_apply(params)

        manager.apply_params_to_workflow = apply_params_to_workflow_with_easyuse_aio
        manager._easyuse_anima_aio_patch_installed = True
        manager._easyuse_anima_aio_original_apply_params_to_workflow = original_apply
        print("✅ EasyUse Anima AiO workflow builder patch installed.")

    @staticmethod
    def _line_text(widget: QLineEdit | None) -> str:
        return widget.text().strip() if widget is not None else ""

    @staticmethod
    def _set_line_text(widget: QLineEdit | None, value: Any):
        if widget is not None and value is not None:
            widget.setText(str(value))
