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

## Install and run

Start the normal tutorial server, then install the core SDK, the separate Strands
adapter, and the example:

```bash
python -m pip install -e ../sdk-python
python -m pip install -e ../sdk-python/packages/aga-strands
python -m pip install -e .
python -m agent_quickstart.worker
```

The first two commands use the sibling source checkouts. A later package release
can replace them with `python -m pip install aga-runtime aga-strands`; this
implementation checkpoint does not publish either package.

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

Provider and framework retries must be kept bounded so they do not multiply Aga's
retry policy. Configure provider connect and response timeouts below the Aga Step's
attempt timeout.

## Mutating tools need their own receipt

Aga can safely reuse the final committed Agent result. It cannot atomically commit
PostgreSQL and an unrelated payment, ticket, email, or infrastructure API. A
mutating Strands tool must call `app.effect(...)` with a stable idempotency key and
support reconciliation when the provider outcome is unknown. Read-only tools do not
need an effect receipt.

This is the **opaque** adapter layer. It does not make each internal model call or
tool call a separate Aga operation, and Strands checkpoints or sessions do not
replace Aga's replay record. Later observed and durable-native layers need their own
approved contracts.
