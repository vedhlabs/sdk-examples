from __future__ import annotations

from typing import Protocol

from agentic.types import Resolution, Ticket


class SupportAgent(Protocol):
    """The small framework-facing contract used by this example adapter."""

    name: str

    async def run(self, ticket: Ticket) -> Resolution:
        raise NotImplementedError


class ScriptedSupportAgent:
    """Offline stand-in for a Strands, Pydantic AI, or LangGraph agent.

    The example stays runnable without an account or model credential. Replace
    this object with a framework agent and adapt its result in one place; the
    Ogha workflow and its approval policy remain unchanged.
    """

    name = "support-triage"

    def __init__(self) -> None:
        self._orders = {
            "customer-42": "order shipped; tracking number ZX-42",
            "customer-99": "order awaiting inventory",
        }

    async def run(self, ticket: Ticket) -> Resolution:
        message = ticket.message.casefold()
        if "refund" in message or ticket.requested_refund:
            amount = ticket.requested_refund
            return Resolution(
                ticket_id=ticket.id,
                category="refund",
                summary=f"Customer requested a refund of {amount}",
                proposed_action=f"refund:{amount}",
                requires_approval=amount >= 100,
            )

        order_status = self._orders.get(ticket.customer_id, "order not found")
        return Resolution(
            ticket_id=ticket.id,
            category="order-status",
            summary=order_status,
            proposed_action="reply-with-order-status",
            requires_approval=False,
        )
