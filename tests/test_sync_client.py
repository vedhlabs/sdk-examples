import json
from types import SimpleNamespace

import ogha
import pytest

from quickstart.sync_client import example_order, run_checkout_sync


class RecordingClient:
    def __init__(self, terminal):
        self.terminal = terminal
        self.calls = []

    def execute(self, workflow, payload, *, run_id, target, wait_timeout_s, poll_s):
        self.calls.append(
            (
                "execute",
                workflow,
                json.loads(payload),
                run_id,
                target,
                wait_timeout_s,
                poll_s,
            )
        )
        return self.terminal


def test_sync_client_executes_once_and_returns_the_terminal_run():
    order = example_order(275, order_id="sync-order-42")
    client = RecordingClient(
        SimpleNamespace(
            run_id="sync-order-42",
            state=ogha.RunState.COMPLETED,
            output=json.dumps({"order_id": "sync-order-42", "total": 275}).encode(),
            error="",
        )
    )

    run_id, output = run_checkout_sync(client, order, timeout_s=12, poll_s=0.5)

    assert run_id == "sync-order-42"
    assert output == {"order_id": "sync-order-42", "total": 275}
    assert client.calls == [
        (
            "execute",
            "quickstart.checkout",
            order,
            "sync-order-42",
            "python://quickstart",
            12,
            0.5,
        ),
    ]


def test_sync_client_surfaces_a_terminal_workflow_failure():
    order = example_order(100, order_id="sync-order-failed")
    client = RecordingClient(
        SimpleNamespace(
            run_id="sync-order-failed",
            state=ogha.RunState.FAILED,
            output=b"",
            error="payment declined",
        )
    )

    with pytest.raises(RuntimeError, match="ended FAILED: payment declined"):
        run_checkout_sync(client, order)
