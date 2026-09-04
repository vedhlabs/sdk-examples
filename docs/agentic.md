# Deferred agent research: one bounded experiment

This credential-free example is retained as research evidence for a future
milestone. Agent integration is not part of the current Ogha release story, and
this example does not claim durable-native model or tool execution.

This package shows the first implemented integration level: an existing agent is
registered as one explicitly **opaque** Ogha step. The example uses a scripted
offline agent so every test runs without a model account; replace it with Strands,
Pydantic AI, LangGraph, or another framework inside the adapter.

```python
app = ogha.App("agentic")
support = app.use(SupportAgentAdapter(existing_agent))

@app.workflow
async def resolve_ticket(ticket: Ticket) -> Resolution:
    proposal = await support.run(ticket)
    if proposal.requires_approval:
        await ogha.approval(
            "agent_action",
            evidence={"ticket": ticket.id, "action": proposal.proposed_action},
            timeout=86_400,
        )
    return proposal
```

The adapter owns its immutable configuration, framework import, and result
conversion. `App.use` owns its stable identity, preflight validation, and any
serve-time lifecycle. Application code sees a typed durable function, not Context,
target, codec, Promise, or worker plumbing.

## Run it

```bash
# terminal 1
python -m agentic.worker

# terminal 2: no approval required
python -m agentic.submit --wait

# A refund of 250 parks on a durable approval.
python -m agentic.submit --ticket-id refund-250 \
  --message "Please refund this order" --refund 250
python -m agentic.operator refund-250 approve
```

## Exact guarantee

Ogha records `example.support-agent/1` and `opaque` on one durable outer operation.
Once its final result commits, recovery reuses that typed result. If the worker or
network fails before it commits, internal model requests and tools can run again.

Therefore this level is suitable for read-only reasoning, idempotent operations,
and adoption before fine-grained integration. A mutating tool still needs a stable
provider idempotency key or reconciliation. Framework hooks may add traces and
token streams, but observation alone does not make model/tool calls replayable.

Future `durable_native` adapters require a separate accepted runtime contract for
stable model/tool identities, semantic fingerprints, one retry owner, explicit
unknown outcomes, reconciliation, and durable final output independent of live
token delivery.
