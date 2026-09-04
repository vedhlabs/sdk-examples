from __future__ import annotations

import ogha

from agentic.app import app, support
from agentic.types import Resolution, Ticket


@app.workflow(name="agentic.resolve-ticket", execution="async_distributed")
async def resolve_ticket(ticket: Ticket) -> Resolution:
    proposal = await support.run(ticket)
    if proposal.requires_approval:
        decision = await ogha.approval(
            "agent_action",
            evidence={
                "ticket_id": ticket.id,
                "agent": support.agent.name,
                "action": proposal.proposed_action,
            },
            timeout=24 * 60 * 60,
        )
        status = "approved" if decision.get("approved") else "rejected"
    else:
        status = "ready"

    result = Resolution(
        ticket_id=proposal.ticket_id,
        category=proposal.category,
        summary=proposal.summary,
        proposed_action=proposal.proposed_action,
        requires_approval=proposal.requires_approval,
        status=status,
    )
    ogha.event(
        "AgentResolutionReady",
        {"ticket_id": ticket.id, "category": result.category, "status": status},
    )
    return result
