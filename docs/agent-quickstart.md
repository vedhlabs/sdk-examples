# Run a Strands Agent as durable work

This example adds durability around a complete Strands Agent invocation. The
workflow stays small:

```python
@app.workflow()
async def investigate(question: str) -> str:
    return await research(question)
```

`research(question)` is one Aga Step. If its result was committed before a worker
crash, Aga replays that result and does not create another Agent. If the invocation
did not commit, Aga may try the whole invocation again. Model calls and tools inside
that unfinished invocation are therefore **at least once**.

## When to use it

Reach for `aga-strands` when an Agent invocation is one unit of durable work: you
want it to survive a worker crash, replay its committed answer instead of paying
for a second inference, stay inside the Namespace's token and cost ceilings, and
have every tool that changes the outside world protected by a receipt. Research,
classification, drafting, a checkout assistant — anything where the *answer* is
what you keep.

Use plain `@app.step` functions when there is no model loop to run; Aga's own
operations are cheaper and fully replayable.

Hold off when you need each model or tool call *inside* the loop to be its own
durable operation — per-call replay, `max_tool_calls` and `max_turns` enforcement,
or an operations timeline of the loop's internals. That is durable-native
execution, which needs the workflow to own the loop and is a separate, still
proposed decision. Opaque mode is honest about the trade: an uncommitted internal
call may repeat after a crash, and only the receipts on mutating tools stop a
repeat from reaching a provider twice.

## Install and run

For this read-only local Agent, either the normal tutorial server or the
source-built development server works. Install the current core SDK, the separate
Strands adapter, and the example:

```bash
python -m pip install -e ../sdk-python
python -m pip install -e ../sdk-python/packages/aga-strands
python -m pip install -e .
python -m agent_quickstart.worker
```

The first two commands use the sibling source checkouts. They are source
candidates, not published package instructions.

From another terminal, submit without waiting:

```bash
python -m agent_quickstart.submit "Why keep a durable record?"
```

Or keep the caller open for the final answer:

```bash
python -m agent_quickstart.submit --wait "Why keep a durable record?"
```

Both commands start the same asynchronous Aga workflow. `--wait` changes only the
caller: it calls `Handle.result()`. Open the dashboard and select the Namespace to
inspect the Run and its `strands.research` Agent operation.

## Why the factory matters

The adapter receives `factory=build_research_agent`, not a process-global Agent.
Strands Agents keep mutable messages and state. The factory gives every Aga attempt
fresh state, including when five Runs execute at the same time.

The default example uses `LocalResearchModel`. It drives the real Strands event loop
but returns a fixed, predictable response and uses no cloud account. See
[`local_model.py`](../src/agent_quickstart/local_model.py) and
[`workflows.py`](../src/agent_quickstart/workflows.py).

## Use Bedrock only when you choose to

[`bedrock.py`](../src/agent_quickstart/bedrock.py) contains an optional real-provider
factory. Give that factory to `strands_adapter.agent(...)`, configure AWS credentials
through the normal provider chain, and set `BEDROCK_MODEL_ID` when you need another
model. Aga does not import or contact Bedrock on its core import path.

Two things this example learned the hard way. Bedrock is regional and Strands
honours `region_name`, so the factory resolves `BEDROCK_REGION`, then `AWS_REGION`,
then `AWS_DEFAULT_REGION`, then `us-east-1` and passes it explicitly — a session
default with no Anthropic access fails permanently, and that is what an earlier run
of this example hit.
And Anthropic models need the account's use-case form filed; until then every call
fails with `ResourceNotFoundException: Model use case details have not been
submitted for this account`, and that state was seen to propagate unevenly across
regions for a while. The default is a single-geo `us.` profile for that reason —
a `global.` profile routes wherever it likes.

Provider and framework retries must be kept bounded so they do not multiply Aga's
retry policy. Configure provider connect and response timeouts below the Aga Step's
attempt timeout.

## Mutating tools need their own receipt

Aga can safely reuse the final committed Agent result. It cannot atomically commit
PostgreSQL and an unrelated payment, ticket, email, or infrastructure API. A
mutating Strands tool must call `app.effect(...)` with a stable idempotency key and
support reconciliation when the provider outcome is unknown. Read-only tools do not
need an effect receipt.

[`tools.py`](../src/agent_quickstart/tools.py) shows the shape, and `checkout` in
[`workflows.py`](../src/agent_quickstart/workflows.py) binds it with a price
function so the Namespace's `max_cost_micros` ceiling can see the agent:

```python
@tool
def charge_card(order_id: str, amount: int) -> str:
    """Charge the customer's card."""
    return app.effect(
        "charge",
        lambda: psp.charge(order_id, amount),
        idempotency_key=f"charge:{order_id}",
        provider="example-psp",
        endpoint="POST /charges",
        request={"order_id": order_id, "amount": amount},
    )

checkout = strands_adapter.agent(
    "checkout",
    factory=build_checkout_agent,       # Agent(model=..., tools=[charge_card])
    model="deterministic-checkout-v1",
    pricer=local_price_micros,          # (model, input_tokens, output_tokens) -> micros
)
```

The key comes from the immutable order identity, not the amount. Two orders for
the same amount are still two external actions, while a retry of one order keeps
the same provider key. The request fingerprint separately catches an accidental
change to that order's amount.

Three things are doing work here. Strands runs `charge_card` on a worker thread,
and `app.effect` still finds the executing Step because the binding is
context-local. The receipt's identity is the idempotency key's digest, so charging
two orders in one invocation yields two receipts rather than one refusal. And the
price function is yours: the adapter ships no rate table, because a stale one
under-reports, which is the one direction a spend ceiling cannot survive.

Run it with the local, cloud-free model:

```bash
python -m agent_quickstart.submit --checkout 1200 --order-id tutorial-order-1 --wait
```

[`local_tool_model.py`](../src/agent_quickstart/local_tool_model.py) asks for the
tool on turn one and confirms on turn two, through Strands' real loop.

The released tutorial server does not advertise effect receipts. Before trying a
mutating tool, stop that tutorial stack and start the contributor stack with
`docker compose up -d`; it builds the sibling server source that implements the
effect contract. Capability negotiation then fails closed if either side is too old.

This is the **opaque** adapter layer. It does not make each internal model call or
tool call a separate Aga operation, and Strands checkpoints or sessions do not
replace Aga's replay record. Later observed and durable-native layers need their own
approved contracts.
