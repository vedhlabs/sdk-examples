"""Check that the blog's two full examples match the runnable source exactly."""

import argparse
import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check(guide: Path) -> None:
    text = guide.read_text()
    for filename in ("first_workflow.py", "checkout_app.py"):
        label = f'<div class="code-file"><code>{filename}</code></div>'
        assert label in text, f"Missing source label: {filename}"
        remainder = text.split(label, 1)[1]
        match = re.search(r"```python\n(.*?)\n```", remainder, re.DOTALL)
        assert match is not None, f"Missing full example: {filename}"
        expected = (ROOT / "src" / "quickstart" / filename).read_text().strip()
        actual = match.group(1).strip()
        ast.parse(actual, filename=filename)
        assert actual == expected, f"Blog code differs from source: {filename}"
        print(f"{filename}: exact source match")

    label = '<div class="code-file"><code>parallel_tasks.py (distributed workflow)</code></div>'
    assert label in text, "Missing parallel task source label"
    match = re.search(r"```python\n(.*?)\n```", text.split(label, 1)[1], re.DOTALL)
    assert match is not None
    source = (ROOT / "src/quickstart/parallel_tasks.py").read_text()
    definition = source.split('@app.workflow(execution="async_distributed")', 1)[1]
    declaration = '@app.workflow(execution="async_distributed")'
    expected = declaration + definition.split("\n\ndef main", 1)[0]
    assert match.group(1).strip() == expected.strip(), "Parallel workflow excerpt differs"
    print("parallel_tasks.py: distributed workflow source match")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("guide", type=Path, help="Path to the blog's aga/python.md")
    check(parser.parse_args().guide)
