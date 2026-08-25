import uuid

from ecommerce.adapters import payments
from trading.adapters.mock import MockBroker


def test_payment_provider_deduplicates_business_key():
    key = f"test:{uuid.uuid4().hex}"
    first = payments.charge("customer", 100, key)
    retry = payments.charge("customer", 100, key)

    assert retry == first


def test_mock_broker_finds_order_by_stable_client_id():
    broker = MockBroker()
    client_id = f"test-{uuid.uuid4().hex}"
    order = {
        "symbol": "AAPL",
        "side": "buy",
        "qty": "1",
        "limit_price": "200",
        "notional": "200",
    }

    placed = broker.place(order, client_id)

    assert broker.find_order(client_id) == placed
    assert broker.place(order, client_id) == placed

