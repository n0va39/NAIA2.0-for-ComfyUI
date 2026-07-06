from __future__ import annotations

import json
import unittest

from naia2_for_comfyui.aio_graph import (
    AIO_GENERATOR_CLASS,
    AIO_GENERATOR_NODE_ID,
    INPUT_CLASS,
    INPUT_NODE_ID,
    PREVIEW_IMAGE_CLASS,
    PREVIEW_NODE_ID,
    PROMPT_DATA_TYPE,
    PROMPT_STUDIO_CLASS,
    PROMPT_STUDIO_NODE_ID,
    build_prompt_from_naia_params,
    normalize_naia_params,
)


class AioGraphTests(unittest.TestCase):
    def test_normalizes_core_naia_params(self):
        params = normalize_naia_params({
            "input": "masterpiece",
            "negative_prompt": "lowres",
            "width": 1023,
            "height": 777,
            "seed": "42",
            "steps": "28",
            "cfg_scale": "4.5",
            "sampler": "euler",
            "model": "ANIMA\\custom.safetensors",
        })

        self.assertEqual(params["prompt"], "masterpiece")
        self.assertEqual(params["negative_prompt"], "lowres")
        self.assertEqual(params["width"], 1024)
        self.assertEqual(params["height"], 768)
        self.assertEqual(params["seed"], 42)
        self.assertEqual(params["steps"], 28)
        self.assertEqual(params["cfg"], 4.5)
        self.assertEqual(params["sampler_name"], "euler")
        self.assertEqual(params["unet_name"], "ANIMA\\custom.safetensors")

    def test_builds_minimum_easyuse_anima_aio_prompt_graph(self):
        graph = build_prompt_from_naia_params({
            "prompt": "1girl, blue sky",
            "negative_prompt": "bad hands",
            "width": 832,
            "height": 1216,
            "seed": 123,
        })

        self.assertEqual(graph[PROMPT_STUDIO_NODE_ID]["class_type"], PROMPT_STUDIO_CLASS)
        self.assertEqual(graph[INPUT_NODE_ID]["class_type"], INPUT_CLASS)
        self.assertEqual(graph[AIO_GENERATOR_NODE_ID]["class_type"], AIO_GENERATOR_CLASS)
        self.assertEqual(graph[PREVIEW_NODE_ID]["class_type"], PREVIEW_IMAGE_CLASS)
        self.assertEqual(
            graph[INPUT_NODE_ID]["inputs"][PROMPT_DATA_TYPE],
            [PROMPT_STUDIO_NODE_ID, 0],
        )
        self.assertEqual(
            graph[AIO_GENERATOR_NODE_ID]["inputs"]["easy_use_anima_input"],
            [INPUT_NODE_ID, 0],
        )
        self.assertEqual(graph[PREVIEW_NODE_ID]["inputs"]["images"], [AIO_GENERATOR_NODE_ID, 0])
        self.assertEqual(graph[PREVIEW_NODE_ID]["_meta"]["title"], "naia_output")

    def test_prompt_studio_uses_naia_values_without_live_naia_fetch(self):
        graph = build_prompt_from_naia_params({
            "prompt": "cat",
            "negative_prompt": "noise",
            "width": 640,
            "height": 960,
        })
        inputs = graph[PROMPT_STUDIO_NODE_ID]["inputs"]
        fields = json.loads(inputs["advanced_fields"])

        self.assertFalse(inputs["use_naia"])
        self.assertFalse(inputs["consume_naia_on_queue"])
        self.assertEqual(inputs["resolution_bucket"], "Custom")
        self.assertEqual(inputs["resolution_custom_width"], 640)
        self.assertEqual(inputs["resolution_custom_height"], 960)
        self.assertEqual(fields[0]["type"], "naia")
        self.assertEqual(fields[0]["text"], "cat")
        self.assertEqual(fields[1]["pane"], "negative")
        self.assertEqual(fields[1]["text"], "noise")

    def test_generation_settings_avoid_optional_node_packs_by_default(self):
        graph = build_prompt_from_naia_params({
            "prompt": "test",
            "steps": 24,
            "cfg": 4,
            "sampler_name": "er_sde",
            "scheduler": "simple",
            "denoise": 0.9,
        })
        settings = json.loads(graph[AIO_GENERATOR_NODE_ID]["inputs"]["generation_settings"])

        self.assertEqual(settings["sampler"]["backend"], "comfy_ksampler")
        self.assertFalse(settings["sampler"]["spectrum"]["enabled"])
        self.assertFalse(settings["sampler"]["dit_corrections"]["enabled"])
        self.assertFalse(settings["model_patches"]["kj"]["torch_compile"]["enabled"])
        self.assertEqual(settings["model_patches"]["kj"]["sage_attention"], "disabled")
        self.assertFalse(settings["highres"]["enabled"])
        self.assertFalse(settings["detailer"]["enabled"])
        self.assertFalse(settings["upscale"]["enabled"])
        self.assertFalse(settings["postprocess"]["enabled"])
        self.assertEqual(settings["save"]["backend"], "comfy_save_image")
        self.assertFalse(settings["save"]["enabled"])

    def test_preview_output_is_used_for_naia_result_lookup(self):
        graph = build_prompt_from_naia_params({
            "prompt": "test",
            "save_enabled": True,
        })

        settings = json.loads(graph[AIO_GENERATOR_NODE_ID]["inputs"]["generation_settings"])
        self.assertFalse(settings["save"]["enabled"])
        self.assertEqual(graph[PREVIEW_NODE_ID]["class_type"], PREVIEW_IMAGE_CLASS)
        self.assertEqual(graph[PREVIEW_NODE_ID]["inputs"]["images"], [AIO_GENERATOR_NODE_ID, 0])
        self.assertEqual(graph[PREVIEW_NODE_ID]["_meta"]["title"], "naia_output")


if __name__ == "__main__":
    unittest.main()
