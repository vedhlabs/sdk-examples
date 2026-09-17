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
`selected_tools` is an application allowlist: a model suggestion is data, not
permission to run arbitrary code. `app.join` admits both check handles before
waiting, so neither check is forced to wait for the other. `publish_decision`
uses a business-stable provider idempotency key and `app.effect`; the local
provider returns the same receipt for the same key. A production provider also
needs bounded network timeouts and an authoritative lookup after an uncertain
response.

## What the gate verifies—and what it does not

The unreleased verified-gate source binds the decision to an exact action,
arguments, generation, expiry, and server-authenticated approver. A generic
`promise.settle` cannot approve it. The server records distinct votes under the
origin transaction; approval waits for quorum, while rejection and expiry fail
closed. The approver uses `client.gates.get(id)` and
`client.gates.decide(question, outcome, command_id=...)`, not a worker or admin
credential. An auth-disabled server cannot decide a verified gate.

The gate does **not** force later application code to call only the approved
effect. This example makes that connection explicitly in the workflow: it checks
the gate result before `publish_decision`. A separate future engine contract
would be needed to bind arbitrary downstream provider calls to the approved
action. This source has local tests, not a production release or hosted identity
integration. Do not treat this pattern alone as authorization for real money or
other high-stakes mutations.

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
