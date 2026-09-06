import asyncio
from pathlib import Path

import pytest

from quickstart import first_workflow


def test_total_and_summary_without_external_services():
    total = first_workflow.calculate_total.__wrapped__([200, 150])
    assert total == 350
    assert first_workflow.make_summary.__wrapped__(total) == "Order total: 350 cents"


@pytest.mark.parametrize("prices", [[], [-1], [200, -150]])
def test_invalid_prices_fail(prices):
    with pytest.raises(ValueError, match="at least one price"):
        first_workflow.calculate_total.__wrapped__(prices)


def test_workflow_awaits_total_before_summary(monkeypatch):
    calls = []

    async def total(prices):
        calls.append(("total", prices))
        return 350

    async def summary(value):
        calls.append(("summary", value))
        return "Order total: 350 cents"

    monkeypatch.setattr(first_workflow, "calculate_total", total)
    monkeypatch.setattr(first_workflow, "make_summary", summary)
    assert asyncio.run(first_workflow.checkout.__wrapped__([200, 150])) == (
        "Order total: 350 cents"
    )
    assert calls == [("total", [200, 150]), ("summary", 350)]


def test_first_example_declares_only_the_introductory_workflow():
    assert set(first_workflow.app._catalog.workflows) == {"checkout"}
    assert first_workflow.checkout.__aga_spec__.execution == "async_sticky"
    assert first_workflow.checkout.__aga_spec__.target == "python://first-workflow"


def test_intro_walkthrough_embeds_the_exact_source():
    root = Path(__file__).resolve().parents[1]
    source = (root / "src/quickstart/first_workflow.py").read_text().strip()
    guide = (root / "docs/first-workflow.md").read_text()
    assert f"```python\n{source}\n```" in guide
