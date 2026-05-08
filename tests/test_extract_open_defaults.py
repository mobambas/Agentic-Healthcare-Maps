from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ExtractOpenDefaultsTest(unittest.TestCase):
    def test_default_qwen_model_uses_t4_safe_awq_model(self) -> None:
        source = (ROOT / "agent" / "extract_open.py").read_text(encoding="utf-8")
        tree = ast.parse(source)

        default_model = None
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "DEFAULT_QWEN_MODEL":
                        default_model = ast.literal_eval(node.value.args[1])

        self.assertEqual(default_model, "Qwen/Qwen2.5-7B-Instruct-AWQ")
