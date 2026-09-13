# External effects and uncertain outcomes

Aga can remember that a Step finished. It cannot place its PostgreSQL commit in
the same transaction as a card network, email service, warehouse, or another
company's API.

Imagine that a provider accepts a charge and the connection drops before the
worker receives the reply. Aga cannot honestly call that a success or a failure.
Wrap the provider call with `app.effect` so the uncertainty becomes a durable
receipt instead of a blind retry:

```python
KEY = f"order:{order['id']}:charge"

return app.effect(
    "charge",
    lambda: provider.charge(
        order,
        idempotency_key=KEY,
        connect_timeout=2,
        read_timeout=8,
    ),
    idempotency_key=KEY,
    provider="payments",
    endpoint="charge",
    request={"order_id": order["id"], "amount": order["total"]},
    not_applied_on=(CardDeclined,),
)
```

`CardDeclined` is illustrative: list an exception in `not_applied_on` only when
the provider contract proves that no change happened. A timeout, connection reset,
HTTP 500, or malformed response is normally uncertain.

After an uncertain outcome, the worker does not call the provider again. A trusted
reconciler follows the original business key:

```python
receipt = provider.find_by_idempotency_key(KEY, timeout=5)
if receipt is not None:
    record_provider_committed(receipt)
elif provider.proved_absent(KEY):
    record_provider_not_applied()
else:
    escalate_for_review()
```

Those final three functions stand for an application-owned operator tool that
submits provider evidence through Aga's effect-reconciliation resource. They are
not extra workflow calls. If Aga records `reconciled_not_applied`, the next replay
may enter the callable inside the same `app.effect` again, using the same key.

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
network request. `app.effect` records what Aga knows, refuses blind re-execution
after an uncertain attempt, and keeps the Run from normal retention while the
question is open. It cannot make a provider idempotent or interrupt a blocked
socket; those remain application and provider responsibilities.
