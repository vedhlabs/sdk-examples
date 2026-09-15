"""A mutating Strands tool with a durable receipt.

Strands runs a synchronous ``@tool`` on an ``asyncio.to_thread`` worker. The Step
binding is context-local, so ``app.effect`` still finds the executing Aga Step from
there — that is what makes a receipt possible inside the framework's own loop.
"""

from strands import tool

from agent_quickstart.app import app


def _psp_charge(amount: int) -> str:
    """Stand-in for a payment provider call. Deterministic; no network."""
    return f"charged {amount} minor units"


@tool
def charge_card(amount: int) -> str:
    """Charge the customer's card.

    Args:
        amount: Amount in minor units, for example cents.
    """
    # The receipt is registered before the call leaves the process and settled
    # after it. If this attempt dies mid-call, the receipt reads `unknown` and a
    # later attempt refuses to charge again until someone reconciles — instead of
    # guessing. The idempotency key is what the provider dedupes on; only its
    # digest is stored, and it also forms the receipt's identity, so charging two
    # different orders in one invocation yields two receipts.
    return app.effect(
        "charge",
        lambda: _psp_charge(amount),
        idempotency_key=f"order-{amount}",
        provider="example-psp",
        endpoint="POST /charges",
    )
