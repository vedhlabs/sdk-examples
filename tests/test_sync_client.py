import ogha
import pytest

from quickstart.sync_client import example_order, run_checkout_sync


class RecordingRun:
    def __init__(self, run_id, output=None, error=None):
        self.id = run_id
        self.output = output
        self.error = error
        self.result_calls = []

    def result(self, timeout, poll):
        self.result_calls.append((timeout, poll))
        if self.error is not None:
            raise self.error
        return self.output


def test_sync_client_starts_once_and_returns_the_typed_result(monkeypatch):
    order = example_order(275, order_id="sync-order-42")
    run = RecordingRun("sync-order-42", {"order_id": "sync-order-42", "total": 275})
    starts = []

    def start(workflow, value):
        starts.append((workflow, value))
        return run

    monkeypatch.setattr("quickstart.sync_client.app.start", start)

    run_id, output = run_checkout_sync(order, timeout_s=12, poll_s=0.5)

    assert run_id == "sync-order-42"
    assert output == {"order_id": "sync-order-42", "total": 275}
    assert starts[0][0].__ogha_workflow_name__ == "quickstart.checkout"
    assert starts[0][0]._options.run_id == "sync-order-42"
    assert starts[0][1] == order
    assert run.result_calls == [(12, 0.5)]


def test_sync_client_surfaces_a_terminal_workflow_failure(monkeypatch):
    order = example_order(100, order_id="sync-order-failed")
    run = RecordingRun("sync-order-failed", error=ogha.OghaError("payment declined"))
    monkeypatch.setattr("quickstart.sync_client.app.start", lambda *_args: run)

    with pytest.raises(ogha.OghaError, match="payment declined"):
        run_checkout_sync(order)
