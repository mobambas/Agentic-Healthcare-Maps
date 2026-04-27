import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _constant_assignment(name: str) -> ast.Assign:
    module = ast.parse((ROOT / "agent" / "extract_open.py").read_text(encoding="utf-8"))
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return node
    raise AssertionError(f"{name} assignment not found")


def test_qwen_default_model_matches_t4_vllm_launch_model() -> None:
    assignment = _constant_assignment("DEFAULT_QWEN_MODEL")

    assert isinstance(assignment.value, ast.Call)
    assert isinstance(assignment.value.func, ast.Attribute)
    assert assignment.value.func.attr == "getenv"
    assert len(assignment.value.args) == 2
    assert ast.literal_eval(assignment.value.args[0]) == "QWEN_MODEL"
    assert ast.literal_eval(assignment.value.args[1]) == "Qwen/Qwen2.5-7B-Instruct-AWQ"
