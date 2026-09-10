# External effects and uncertain outcomes

Aga can remember that a Step finished. It cannot place its PostgreSQL commit in
the same transaction as a card network, email service, warehouse, or another
company's API.

Imagine that a provider accepts a charge and the connection drops before the
worker receives the reply. Aga has no receipt to checkpoint, so the Step may run
again. The safe adapter does not guess whether the charge happened:

```python
KEY = f"order:{order['id']}:charge"

try:
    receipt = provider.charge(
        order,
        idempotency_key=KEY,
        connect_timeout=2,
        read_timeout=8,
    )
except ProviderConnectionLost:
    receipt = provider.find_by_idempotency_key(KEY, timeout=5)
    if receipt is None and provider.proved_absent(KEY):
        receipt = provider.charge(
            order,
            idempotency_key=KEY,
            connect_timeout=2,
            read_timeout=8,
        )
    elif receipt is None:
        raise OutcomeStillUnknown(KEY)

return receipt
```

The exception names are illustrative because every provider library differs. The
order of decisions is the contract:

1. Create one key from stable business identity and effect purpose. Do not put an
   attempt number, process ID, or current time in it.
2. Configure the network client itself with finite connect, pool, write, and read
   deadlines. Aga's Step and attempt limits do not interrupt a blocked socket.
3. After an uncertain response, query the provider by the original key.
4. Return the existing receipt when found. Retry only after an authoritative
   “absent” answer, and use the same key.
5. Leave an unknowable result unresolved and reconcile or review it. A new key can
   create a second real-world effect.

The checkout mock makes the two useful provider operations concrete:

- [`payments.charge`](../src/checkout/adapters/payments.py) applies an effect once
  for a stable key;
- [`payments.find_charge`](../src/checkout/adapters/payments.py) retrieves the
  original receipt without applying the effect again.

[`ExampleStore`](../src/example_support/store.py) is a tiny SQLite stand-in for a
provider. Its database is deliberately separate from Aga so retry behavior stays
honest. A real integration should also run a reconciliation job that finds
business operations without an Aga receipt, looks them up by key, and records or
escalates the provider's answer.

`client.apply_once` only reserves an Aga-side key. It cannot atomically wrap a
network request. Aga does not currently expose an `app.effect` API; such a public
cross-SDK, wire, and storage contract remains a separate decision.
