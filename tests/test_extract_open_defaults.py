from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_MODEL = "Qwen/Qwen2.5-7B-Instruct-AWQ"


class ExtractOpenDefaultsTest(unittest.TestCase):
    def test_default_qwen_model_uses_awq(self) -> None:
        tree = ast.parse((ROOT / "agent" / "extract_open.py").read_text(encoding="utf-8"))

        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            if not any(isinstance(target, ast.Name) and target.id == "DEFAULT_QWEN_MODEL" for target in node.targets):
                continue

            self.assertIsInstance(node.value, ast.Call)
            self.assertGreaterEqual(len(node.value.args), 2)
            self.assertIsInstance(node.value.args[1], ast.Constant)
            self.assertEqual(node.value.args[1].value, EXPECTED_MODEL)
            return

        self.fail("DEFAULT_QWEN_MODEL assignment not found")

    def test_default_model_matches_colab_notebook(self) -> None:
        notebook = json.loads(
            (ROOT / "notebooks" / "colab_qwen_extraction.ipynb").read_text(encoding="utf-8")
        )

        start_cell = next(
            cell
            for cell in notebook["cells"]
            if cell.get("id") == "start-vllm"
        )
        source = "".join(start_cell["source"])

        self.assertIn(f"MODEL_NAME = '{EXPECTED_MODEL}'", source)


if __name__ == "__main__":
    unittest.main()
