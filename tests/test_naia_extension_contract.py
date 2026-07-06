from __future__ import annotations

from pathlib import Path
import unittest


class NaiaExtensionContractTests(unittest.TestCase):
    def test_module_uses_naia2_middle_extension_contract(self):
        source = Path("modules/easyuse_anima_aio_module.py").read_text(encoding="utf-8")

        self.assertIn("class EasyUseAnimaAioModule(BaseMiddleModule, ModeAwareModule)", source)
        self.assertIn("self.COMFYUI_compatibility = True", source)
        self.assertIn("def initialize_with_context(self, context)", source)
        self.assertIn("def get_parameters(self)", source)
        self.assertIn('"workflow_type": "easyuse_anima_aio"', source)
        self.assertIn("_install_workflow_builder_patch", source)
        self.assertIn("build_prompt_from_naia_params(params)", source)


if __name__ == "__main__":
    unittest.main()
