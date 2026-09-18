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
for a second inference, and report tokens against the Namespace's ceiling. A
cost ceiling also needs a reviewed price function; the Bedrock example does not
provide one. Use an effect receipt when an Agent invokes a mutating tool.
Research, classification, drafting, and checkout assistance are examples where
the *answer* is what you keep.

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

Use the current source-built development server with this source SDK; the released
0.2.1 server has a different wire generation. Install the current core SDK, the
separate Strands adapter, and the example:

From `sdk-examples`, start the [contributor stack](../README.md#build-the-development-stack-contributors)
with `docker compose up -d`, then run:

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

[`bedrock.py`](../src/agent_quickstart/bedrock.py) contains the real-provider
factory. The separate [`bedrock_workflows.py`](../src/agent_quickstart/bedrock_workflows.py)
registers it only when `AGA_AGENT_BEDROCK=1`; the default worker stays cloud-free.
Stop the default example worker before starting this one.
Use normal AWS credentials (for example, an SSO profile), and set both the model
and Region explicitly in **each** terminal. A confirmed Mumbai test uses:

```bash
export AGA_AGENT_BEDROCK=1
export BEDROCK_REGION=ap-south-1
export BEDROCK_MODEL_ID=global.anthropic.claude-haiku-4-5-20251001-v1:0
python -m agent_quickstart.worker
```

From another terminal, with the same environment and virtual environment:

```bash
export AGA_AGENT_BEDROCK=1
export BEDROCK_REGION=ap-south-1
export BEDROCK_MODEL_ID=global.anthropic.claude-haiku-4-5-20251001-v1:0
python -m agent_quickstart.submit --bedrock --wait "Explain durable execution in one sentence."
```

This is a real, billable model call. The `global.` profile can process the prompt
outside India despite the `ap-south-1` endpoint; use synthetic input only unless
that routing meets your data policy. The `us.` Haiku profile is not a Mumbai
inference option. Aga does not import or contact Bedrock on its core import path.
The example records token usage but has no Bedrock price function, so it does not
claim an enforced cost ceiling; supply a reviewed `pricer` before production use.

Two things this example learned the hard way. Bedrock is regional and Strands
honours `region_name`, so the factory resolves `BEDROCK_REGION`, then `AWS_REGION`,
then `AWS_DEFAULT_REGION`, then `us-east-1` and passes it explicitly when used
standalone. The runnable Bedrock workflow requires `BEDROCK_REGION` and
`BEDROCK_MODEL_ID`, so it never silently uses those fallback defaults.
And Anthropic models need the account's use-case form filed; until then every call
fails with `ResourceNotFoundException: Model use case details have not been
submitted for this account`, and that state was seen to propagate unevenly across
regions for a while. The standalone factory's default is a `us.` profile, which
is not valid for the Mumbai example; its explicit `global.` selection is deliberate.

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
tool on turn one and confirms on turn two, through Strands' real loop. It raises
instead of claiming checkout succeeded when Strands returns a tool error. For a
real model, do not treat a fluent final answer as proof that a payment or other
external action happened: verify the provider outcome and the Aga effect receipt.

The released tutorial server does not advertise effect receipts. Before trying a
mutating tool, use the source-built contributor stack from the setup above. It
builds the sibling server source that implements the effect contract. Capability
negotiation fails closed if either side is too old.

This is the **opaque** adapter layer. It does not make each internal model call or
tool call a separate Aga operation, and Strands checkpoints or sessions do not
replace Aga's replay record. Later observed and durable-native layers need their own
approved contracts.
