from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class FakeContext:
    def __init__(self, settings=None, api_mode="COMFYUI"):
        self.settings = dict(settings or {})
        self.api_mode = api_mode
        self.panel = None
        self.action_handler = None
        self.subscriptions = {}
        self.cancelled = []
        self.enqueued = []
        self.toasts = []

    def load_settings(self, defaults=None):
        data = dict(defaults or {})
        data.update(self.settings)
        return data

    def register_panel(self, fields, *, title=None, on_action=None, hide_arm_when=None):
        self.panel = {"fields": list(fields), "title": title, "hide_arm_when": hide_arm_when}
        self.action_handler = on_action

    def subscribe(self, event_name, callback, **kwargs):
        self.subscriptions[event_name] = callback

    def get_current_request(self):
        return {
            "ok": True,
            "api_mode": self.api_mode,
            "prompt_run_id": "run-1",
            "params": {
                "input": "masterpiece",
                "negative_prompt": "lowres",
                "width": 832,
                "height": 1216,
                "seed": 123,
            },
        }

    def cancel_generation(self, request_id):
        self.cancelled.append(request_id)
        return {"ok": True, "message": ""}

    def enqueue_generation(self, **kwargs):
        self.enqueued.append(kwargs)
        return {"ok": True, "request_id": "ext-1", "message": ""}

    def show_toast(self, message, level="info"):
        self.toasts.append((level, message))


def load_main_module():
    spec = importlib.util.spec_from_file_location("naia2_for_comfyui_ext_main", ROOT / "main.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class NaiaExtensionContractTests(unittest.TestCase):
    def test_manifest_uses_naia_portable_extension_contract(self):
        manifest = json.loads((ROOT / "extension.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest["id"], "naia2_easyuse_anima_aio")
        self.assertEqual(manifest["naia_ext_api"], 1)
        self.assertEqual(manifest["entry"], "main.py")
        self.assertTrue((ROOT / manifest["entry"]).is_file())

    def test_main_registers_panel_and_generation_hook(self):
        module = load_main_module()
        ctx = FakeContext()

        module.register(ctx)

        self.assertIn("generation_request_dispatched", ctx.subscriptions)
        self.assertIsNotNone(ctx.panel)
        field_keys = {field["key"] for field in ctx.panel["fields"]}
        self.assertIn("auto_override", field_keys)
        self.assertIn("allow_workflow_overwrite", field_keys)
        self.assertIn("generate_now", field_keys)
        self.assertNotIn("save_enabled", field_keys)
        self.assertNotIn("filename_prefix", field_keys)

    def test_generate_action_queues_direct_aio_workflow(self):
        module = load_main_module()
        ctx = FakeContext()
        module.register(ctx)

        ctx.action_handler("generate_now")

        self.assertEqual(len(ctx.enqueued), 1)
        queued = ctx.enqueued[0]
        workflow = queued["overrides"]["workflow"]
        self.assertEqual(queued["api_mode"], "COMFYUI")
        self.assertEqual(queued["prompt"], "masterpiece")
        self.assertEqual(queued["negative_prompt"], "lowres")
        self.assertEqual(workflow["3"]["class_type"], "EasyUseAnimaAIOGenerator")
        self.assertEqual(workflow["4"]["class_type"], "PreviewImage")
        self.assertEqual(queued["overrides"]["_comfyui_output_node_id"], "4")

    def test_normal_generate_hook_cancels_and_requeues_aio_workflow(self):
        module = load_main_module()
        ctx = FakeContext(settings={"auto_override": True})
        module.register(ctx)

        ctx.subscriptions["generation_request_dispatched"]({
            "request_id": "req-1",
            "api_mode": "COMFYUI",
            "priority": 2,
            "prompt_run_id": "run-1",
            "params": {
                "input": "1girl",
                "negative_prompt": "bad anatomy",
                "width": 1024,
                "height": 1024,
            },
        })

        self.assertEqual(ctx.cancelled, ["req-1"])
        self.assertEqual(len(ctx.enqueued), 1)
        self.assertEqual(ctx.enqueued[0]["priority"], 2)
        self.assertEqual(ctx.enqueued[0]["prompt_run_id"], "run-1")
        self.assertIn("workflow", ctx.enqueued[0]["overrides"])

    def test_existing_custom_workflow_is_not_overwritten_by_default(self):
        module = load_main_module()
        ctx = FakeContext(settings={"auto_override": True, "allow_workflow_overwrite": False})
        module.register(ctx)

        ctx.subscriptions["generation_request_dispatched"]({
            "request_id": "req-1",
            "api_mode": "COMFYUI",
            "params": {
                "input": "1girl",
                "comfyui_workflow_has_custom": True,
            },
        })

        self.assertEqual(ctx.cancelled, [])
        self.assertEqual(ctx.enqueued, [])
        self.assertTrue(ctx.toasts)


if __name__ == "__main__":
    unittest.main()
