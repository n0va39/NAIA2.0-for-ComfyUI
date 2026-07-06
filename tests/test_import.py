from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


class ImportTests(unittest.TestCase):
    def test_imports_with_comfyui_directory_module_name(self):
        root = Path(__file__).resolve().parents[1]
        module_name = str(root).replace(".", "_x_")
        spec = importlib.util.spec_from_file_location(
            module_name,
            root / "__init__.py",
            submodule_search_locations=[str(root)],
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        finally:
            sys.modules.pop(module_name, None)

        self.assertEqual(module.WEB_DIRECTORY, "./web")
        self.assertEqual(module.NODE_CLASS_MAPPINGS, {})


if __name__ == "__main__":
    unittest.main()
