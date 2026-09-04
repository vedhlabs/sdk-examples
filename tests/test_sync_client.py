import ogha
import pytest

from quickstart.sync_client import example_order, run_checkout_sync


class RecordingRun:
    def __init__(self, run_id, output=None, error=None):
        self.id = run_id
        self.output = output
        self.error = error
        self.run_calls = []

    def run(self, value):
        self.run_calls.append(value)
        if self.error is not None:
            raise self.error
        return self.output


def test_sync_client_starts_once_and_returns_the_typed_result(monkeypatch):
    order = example_order(275, order_id="sync-order-42")
    run = RecordingRun("sync-order-42", {"order_id": "sync-order-42", "total": 275})
    calls = []

    class ConfiguredCheckout:
        def run(self, value):
            calls.append(("run", value))
            return run.run(value)

    def options(*, run_id):
        calls.append(("options", run_id))
        return ConfiguredCheckout()

    monkeypatch.setattr("quickstart.sync_client.checkout.options", options)

    run_id, output = run_checkout_sync(order)

    assert run_id == "sync-order-42"
    assert output == {"order_id": "sync-order-42", "total": 275}
    assert calls == [("options", "sync-order-42"), ("run", order)]
    assert run.run_calls == [order]


def test_sync_client_surfaces_a_terminal_workflow_failure(monkeypatch):
    order = example_order(100, order_id="sync-order-failed")
    run = RecordingRun("sync-order-failed", error=ogha.OghaError("payment declined"))

    class ConfiguredCheckout:
        def run(self, value):
            return run.run(value)

    monkeypatch.setattr(
        "quickstart.sync_client.checkout.options", lambda **_options: ConfiguredCheckout()
    )

    with pytest.raises(ogha.OghaError, match="payment declined"):
        run_checkout_sync(order)
