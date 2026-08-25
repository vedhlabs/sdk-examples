import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_every_public_documentation_page_has_existing_canonical_sources():
    coverage = json.loads((ROOT / "docs/coverage.json").read_text())

    assert set(coverage) == {
        "src/pages/ogha/index.md",
        "src/pages/ogha/python.md",
        "src/pages/ogha/use-cases/index.md",
        "src/pages/ogha/use-cases/order.md",
        "src/pages/ogha/use-cases/lending.md",
        "src/pages/ogha/use-cases/trading.md",
    }
    for paths in coverage.values():
        assert paths
        for relative in paths:
            assert (ROOT / relative).is_file(), relative


def test_runnable_python_has_no_empty_function_bodies():
    for path in (ROOT / "src").rglob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            assert not any(isinstance(statement, ast.Pass) for statement in node.body), path
            if path.name != "broker.py":
                assert not any(
                    isinstance(statement, ast.Expr)
                    and isinstance(statement.value, ast.Constant)
                    and statement.value.value is Ellipsis
                    for statement in node.body
                ), path

