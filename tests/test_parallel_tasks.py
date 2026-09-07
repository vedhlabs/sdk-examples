import asyncio
from pathlib import Path

import pytest

from quickstart import parallel_tasks


def test_given_demo_steps_when_invoked_then_results_identify_the_task(monkeypatch):
    monkeypatch.setattr(parallel_tasks.time, "sleep", lambda _seconds: None)
    assert parallel_tasks.check_stock.__wrapped__("order-1")["check"] == "stock"
    shipping = parallel_tasks.quote_shipping.__wrapped__("order-1")
    assert shipping["check"] == "shipping"
    assert shipping["order_id"] == "order-1"
    assert shipping["finished_ns"] >= shipping["started_ns"]


@pytest.mark.parametrize(
    "workflow", [parallel_tasks.sticky_checks, parallel_tasks.distributed_checks],
)
def test_given_two_tasks_when_workflow_runs_then_both_calls_precede_join(monkeypatch, workflow):
    calls = []
    stock, shipping = object(), object()

    def check(order_id):
        calls.append(("stock", order_id))
        return stock

    def quote(order_id):
        calls.append(("shipping", order_id))
        return shipping

    async def join(*handles):
        assert handles == (stock, shipping)
        assert calls == [("stock", "order-1"), ("shipping", "order-1")]
        return [{"available": True}, {"cost": 50}]

    monkeypatch.setattr(parallel_tasks, "check_stock", check)
    monkeypatch.setattr(parallel_tasks, "quote_shipping", quote)
    monkeypatch.setattr(parallel_tasks.aga, "join", join)
    assert asyncio.run(workflow.__wrapped__("order-1")) == {
        "stock": {"available": True}, "shipping": {"cost": 50},
    }


def test_given_modes_when_declared_then_waiting_is_not_a_third_placement():
    assert parallel_tasks.sticky_checks.__aga_spec__.execution == "async_sticky"
    assert parallel_tasks.distributed_checks.__aga_spec__.execution == "async_distributed"


def test_given_documented_core_example_when_read_then_it_matches_source():
    root = Path(__file__).resolve().parents[1]
    source = (root / "src/quickstart/parallel_tasks.py").read_text()
    assert 'app = aga.App("parallel-tasks", concurrency=8)' in source
    assert source.count("await aga.join(stock_task, shipping_task)") == 2
