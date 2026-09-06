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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("guide", type=Path, help="Path to the blog's aga/python.md")
    check(parser.parse_args().guide)
