# A workflow-owned agent pattern

This small, credential-free example lets the workflow own the order of an
agent-like decision. It commits a proposed tool list, runs two read-only checks
in parallel, applies an allowlisted policy, waits for a manual answer, and only
then calls a local provider under an effect receipt. The model is a deterministic
stand-in so that you can run and inspect the pattern without buying inference.

```text
propose_checks (MODEL Step)
        |
        +-- identity_check (TOOL Step) --+
        +-- watchlist_check (TOOL Step) -+-- join -- policy_check
                                                   |
                                      blocked -----+----- allowed
                                                               |
                                                   manual gate / timeout
                                                               |
                                                   publish_decision (effect)
```

Start a current source-built Aga server and PostgreSQL, then install this repo
and the sibling SDK. From `sdk-examples`:

```bash
python -m pip install -e ../sdk-python
python -m pip install -e '.[dev]'
export AGA_URL=http://127.0.0.1:8080
make smoke-agent-pattern
```

The smoke provisions a fresh Namespace, starts a worker, and checks four cases:
approved, policy-blocked, denied, and expired. It verifies that the provider has not
changed before the manual answer and that replay after a worker restart does not
make a second provider call. It also sends the same local manual answer twice to
exercise idempotent settlement. Each run is visible under its printed Namespace ID
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

## Important approval boundary

This is a **local manual-gate demonstration, not a production approval system**.
The current server accepts a generic `promise.settle` for a gate, and a writer
credential can submit a value such as `{"approved":true}`. It does not yet
verify a human identity, eligible claims, action digest, or quorum on that
settlement. An auth-disabled local server has no human identity to verify at
all. The Python `Approval` value makes the proposed action visible and replay-
stable, but it cannot turn a generic write credential into an authorized
approver. Do not use this pattern to release real external mutations on the
strength of the gate alone. Production use needs a server-side, actor-bound
approval decision operation and tests that reject generic settlement of gates.

## Language-neutral contract

The durability boundaries are not Python decorators. The kernel stores a Run,
positioned Promises and Tasks, a manual gate Promise, and an effect receipt.
`model`, `tool`, and `gate` are operation-class metadata, not new execution
state machines. The wire already defines operation classes, agent ceilings,
effect states and CBOR effect operations, so another SDK can lower its native
syntax into those same records. Each SDK must preserve the same replay identity,
commit-before-next-tool ordering, and provider idempotency key.

| Boundary | Python source candidate | Go / Java today |
| --- | --- | --- |
| Workflow and parallel durable Steps | `@app.workflow`, `@app.step`, `app.join` | Existing workflow/handle APIs have parallel joins. |
| Model/tool classification | `operation_class=MODEL/TOOL` | Wire tag exists; SDK parity is not yet implemented. |
| Exact-action approval proposal | `app.signal(Approval(...))` | Generic gates exist, but proposal/receipt parity and server verification are not implemented. |
| Mutating effect receipt | `app.effect(...)` | Wire effect band exists; SDK parity is not yet implemented. |

This table is a compatibility checklist, not a claim that the Go or Java SDKs
already expose the full agent pattern. The next shared contract should be the
server-verified approval decision. It must be defined on the wire and tested
against a non-admin, authenticated deployment before any language claims
production approval support.
