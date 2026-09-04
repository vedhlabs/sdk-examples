from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Ticket:
    id: str
    customer_id: str
    message: str
    requested_refund: int = 0


@dataclass(frozen=True)
class Resolution:
    ticket_id: str
    category: str
    summary: str
    proposed_action: str
    requires_approval: bool
    status: str = "proposed"
