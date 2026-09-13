import uuid

import pytest
from aga_runtime import errors

from checkout.adapters import payments as checkout_payments
from checkout.adapters import shipping
from checkout.app import app
from checkout.workflows import charge_order, create_shipment
from ecommerce.adapters import payments
from trading.adapters.mock import MockBroker


def test_payment_provider_deduplicates_business_key():
    key = f"test:{uuid.uuid4().hex}"
    first = payments.charge("customer", 100, key)
    retry = payments.charge("customer", 100, key)

    assert retry == first


def test_shipping_provider_recovers_the_original_receipt_by_business_key():
    key = f"test:{uuid.uuid4().hex}"
    order = {"id": f"order-{uuid.uuid4().hex}"}
    first = shipping.create(order, key)

    assert shipping.find_shipment(key) == first
    assert shipping.create(order, key) == first


def test_reconciled_charge_recovers_the_provider_receipt(monkeypatch):
    order = {
        "id": f"order-{uuid.uuid4().hex}",
        "customer_id": "customer",
        "total": 100,
    }
    key = f"order:{order['id']}:charge"
    receipt = checkout_payments.charge("customer", 100, key)

    def already_applied(*_args, **_kwargs):
        raise errors.EffectAlreadyApplied("reconciled committed")

    monkeypatch.setattr(app, "effect", already_applied)

    assert charge_order.__wrapped__(order) == receipt


def test_reconciled_shipment_without_provider_receipt_stays_failed(monkeypatch):
    order = {"id": f"order-{uuid.uuid4().hex}"}

    def already_applied(*_args, **_kwargs):
        raise errors.EffectAlreadyApplied("reconciled committed")

    monkeypatch.setattr(app, "effect", already_applied)

    with pytest.raises(errors.EffectAlreadyApplied):
        create_shipment.__wrapped__(order)


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
