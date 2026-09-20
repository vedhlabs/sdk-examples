# A workflow-owned agent pattern

This small example lets the workflow own the order of an
agent-like decision. It commits a proposed tool list, runs two read-only checks
in parallel, applies an allowlisted policy, waits for a verified answer, and only
then calls a local provider under an effect receipt. The model is a deterministic
stand-in so that you can run and inspect the pattern without buying inference.
The server still needs separate worker and approver credentials.

```text
propose_checks (MODEL Step)
        |
        +-- identity_check (TOOL Step) --+
        +-- watchlist_check (TOOL Step) -+-- join -- policy_check
                                                   |
                                      blocked -----+----- allowed
                                                               |
                                               verified gate / timeout
                                                               |
                                                   publish_decision (effect)
```

Start a current source-built Aga server and PostgreSQL with authentication and
the dedicated read-only maintenance identity enabled. Provision a Namespace,
then put two credentials in the server keyfile for that Namespace: a `worker`
key, and an `approver` key with a stable actor ID. Do not give the worker key
the approver role. The workflow requires the approver's verified `team:risk`
claim. `agad keygen` prints each secret once and a hashed keyfile entry; combine
the worker and approver entries under one `keys` array, then start the server
with `--auth-keys` pointing at that file:

```bash
agad keygen --role worker --id agent-pattern-worker --namespaces your-namespace-id
agad keygen --role approver --id alice --namespaces your-namespace-id --claims team:risk
```

Keep both secrets out of source control. From `sdk-examples`:

```bash
python -m pip install -e ../sdk-python
python -m pip install -e '.[dev]'
export AGA_URL=http://127.0.0.1:8080
export AGA_NAMESPACE=your-provisioned-namespace-id
export AGA_API_KEY=your-worker-key
export AGA_APPROVER_KEY=your-approver-key
make smoke-agent-pattern
```

The smoke uses that Namespace, starts a worker, and checks four cases:
approved, policy-blocked, denied, and expired. It verifies that the provider has not
changed before the verified answer and that replay after a worker restart does not
make a second provider call. It also retries the same approver command to
exercise idempotent decision commit. Each run is visible under its printed Namespace ID
in the dashboard. To experiment manually, start
`python -m agent_pattern.worker` with your chosen `AGA_NAMESPACE`.

Read [`workflows.py`](../src/agent_pattern/workflows.py) from top to bottom.

## Let one agent session outlive one Run

An agent can talk, research, or supervise work for much longer than one safe
replay history. [`session_workflow.py`](../src/agent_pattern/session_workflow.py)
keeps the application loop ordinary: plan one turn, start two independent tools,
join them, then commit a summary. After two turns it asks Aga to continue the same
logical session in a fresh physical Run:

```python
if turn < max_turns and completed_here >= turns_per_generation:
    app.continue_as_new(research_session, next_state)
```

The call does not return. Aga atomically completes the current generation and
starts the next one with `next_state`. The original Handle follows those links to
the final answer. Only one root generation may be active for a `session_id`, so a
second caller gets an explicit conflict instead of silently interleaving another
writer into the conversation. The example carries counters and only the eight
most recent turn summaries; continuation bounds execution history, but the
application must also keep its carried state bounded.

Start the same worker, then submit six turns split across three generations:

```bash
python -m agent_pattern.worker
```

```bash
python -m agent_pattern.session_submit --turns 6 --turns-per-generation 2 --wait
```

Open the printed initial Run in the console. **Execution family** shows all three
generations, every model/tool operation, and the child workflows belonging to
each generation on one time axis. This example uses deterministic local Steps so
it is free and repeatable; replace `plan_turn` and `summarize_turn` with complete
model calls without moving the loop into framework-private middleware.
`selected_tools` is an application allowlist: a model suggestion is data, not
permission to run arbitrary code. `app.join` admits both check handles before
waiting, so neither check is forced to wait for the other. `publish_decision`
uses a business-stable provider idempotency key and `app.effect`; the local
provider returns the same receipt for the same key. A production provider also
needs bounded network timeouts and an authoritative lookup after an uncertain
response.

## Drive a long-lived session with commands

Continuation gives a session a longer life, but it does not give callers an
ordered inbox. [`command_session.py`](../src/agent_pattern/command_session.py)
shows that second boundary. Its ordinary loop waits for the next authenticated
command, runs one durable agent Step, records a safe completion fact, and moves
to a fresh Run after a bounded number of commands:

```python
while True:
    command = await app.command(timeout=3600)
    if command.kind == "stop":
        return final_result
    result = await handle_command(command.command_id, command.kind, command.payload)
    if handled_here >= commands_per_generation:
        app.continue_as_new(command_session, next_state)
```

`app.command` is a durable Workflow operation, not a process queue. The server
binds the oldest queued command to its exact Promise in one PostgreSQL
transaction. If the worker dies after that commit, recovery replays the same
command. It does not consume the next one. The command being **delivered** only
means Workflow code can replay it; the later Step or Workflow result records
whether the application actually completed the work.

Register desired state once with an administrator credential, then run the
worker and start a session:

```bash
export AGA_RELEASE=mailbox-example-v1
export AGA_MANIFEST_DIGEST=sha256:mailbox-example-v1
export AGA_ADMIN_KEY=your-admin-key       # omit only on an auth-disabled local stack
python -m agent_pattern.fleet_register

python -m agent_pattern.worker
python -m agent_pattern.mailbox_submit --session-id demo-conversation
```

Send two messages and stop the session from another terminal. A writer
credential belongs in `AGA_API_KEY`; actor identity comes from that credential,
not from command JSON:

```bash
python -m agent_pattern.mailbox_send demo-conversation "review application 42"
python -m agent_pattern.mailbox_send demo-conversation "summarize the evidence"
python -m agent_pattern.mailbox_send demo-conversation --kind stop
```

The sender reads the current mailbox revision, submits a stable command ID, and
rereads once if another writer wins the revision race. Use `--command-id` when a
caller may retry after losing an HTTP response. The same ID and content are
idempotent; changing the content behind that ID is a conflict.

Open **Agents** in the console. The agent row compares the registered release,
manifest, replicas, and concurrency with worker heartbeats. Aga reports missing,
extra, draining, gone, and mismatched workers; Docker, ECS, EKS, AgentCore, or
another process manager still decides how many workers actually run. Select the
session beneath that row to inspect every queued, delivered, or canceled command
and follow its delivered Run into the execution workbench.

The automated source-stack proof starts a worker, delivers one command, stops
and restarts the worker around another command, crosses continuation generations,
and then stops cleanly:

```bash
make smoke-command-mailbox
```

The mailbox has bounded payload, identifier, page, and queued-depth limits.
History follows the retained logical session across Run generations. Reset will
not discard a delivered command operation, because doing so would leave durable
mailbox history claiming input was consumed while replay waited forever.

## What the gate verifies—and what it does not

The unreleased verified-gate source binds the decision to an exact action,
arguments, generation, expiry, and server-authenticated approver. A generic
`promise.settle` cannot approve it. The server records distinct votes under the
origin transaction; approval waits for quorum, while rejection and expiry fail
closed. The approver uses `client.gates.get(id)` and
`client.gates.decide(question, outcome, command_id=...)`, not a worker or admin
credential. An auth-disabled server cannot decide a verified gate.

The workflow passes the gate Handle's ID into `publish_decision`, which passes
it to `app.effect` alongside the exact provider, action, and request shown to
the approver. The engine checks those fields and the verified vote, then records
the gate's one-effect binding and effect receipt in one origin transaction. A
different effect ID cannot reuse that vote; a worker-supplied boolean cannot
authorize a gated effect. The gate does **not** prevent arbitrary Python code
from making a direct provider call outside `app.effect`, so the application's
provider adapter must keep all mutations inside that boundary. This source has
local tests, not a production release or hosted identity integration. Do not
treat this pattern alone as authorization for real money or other high-stakes
mutations.

## Language-neutral contract

The durability boundaries are not Python decorators. The kernel stores a Run,
positioned Promises and Tasks, a verified gate Promise, and an effect receipt.
`model`, `tool`, and `gate` are operation-class metadata, not new execution
state machines. The wire already defines operation classes, agent ceilings,
effect states and CBOR effect operations, so another SDK can lower its native
syntax into those same records. Each SDK must preserve the same replay identity,
commit-before-next-tool ordering, and provider idempotency key.

| Boundary | Python source candidate | Go / Java today |
| --- | --- | --- |
| Workflow and parallel durable Steps | `@app.workflow`, `@app.step`, `app.join` | Existing workflow/handle APIs have parallel joins. |
| Model/tool classification | `operation_class=MODEL/TOOL` | Wire tag exists; SDK parity is not yet implemented. |
| Exact-action approval proposal | `app.signal(Approval(...))` | Go and Java can read and decide the same versioned gate contract; language-native authoring parity remains separate. |
| Mutating effect receipt | `app.effect(...)` | Wire effect band exists; SDK parity is not yet implemented. |

This table is a compatibility checklist, not a claim that the Go or Java SDKs
already expose the full agent pattern. Python, Go, Java, and the wire have a
shared CBOR/digest fixture; the verified decision has local authenticated
PostgreSQL tests. A deployment's approver identity, revocation, audit retention,
and provider action binding still need their own production review.
