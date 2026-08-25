from __future__ import annotations

import time

import ogha


def pending_promise(client: ogha.Client, run_id: str, label: str, timeout_s: float = 10.0):
    """Poll until the named external wait or gate is visible and pending."""
    deadline = time.monotonic() + timeout_s
    needle = f".{label}."
    while time.monotonic() < deadline:
        _, promises, _ = client.status(run_id)
        match = next(
            (
                promise
                for promise in promises
                if needle in promise.id and promise.state is ogha.PromiseState.PENDING
            ),
            None,
        )
        if match is not None:
            return match
        time.sleep(0.1)
    raise TimeoutError(f"run {run_id!r} did not expose pending promise {label!r}")

