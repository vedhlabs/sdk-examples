from example_support.store import ExampleStore, stable_id


def test_once_returns_first_result_and_counts_retries(tmp_path):
    store = ExampleStore(str(tmp_path / "provider.sqlite3"))

    first = store.once("payments", "order-1", lambda: {"charge": "first"})
    retry = store.once("payments", "order-1", lambda: {"charge": "second"})

    assert first == {"charge": "first"}
    assert retry == first
    assert store.effect_calls("payments", "order-1") == 2


def test_stable_id_is_deterministic_and_scoped_by_prefix():
    assert stable_id("charge", "order-1") == stable_id("charge", "order-1")
    assert stable_id("charge", "order-1") != stable_id("shipment", "order-1")

