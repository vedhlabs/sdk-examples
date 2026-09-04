from __future__ import annotations

import time

from aga_runtime.client import Client
from aga_runtime.protocol.wire import PromiseState


def pending_promise(client: Client, run_id: str, label: str, timeout_s: float = 10.0):
    """Poll until the named external wait or gate is visible and pending."""
    deadline = time.monotonic() + timeout_s
    needle = f".{label}."
    while time.monotonic() < deadline:
        _, promises, _ = client.status(run_id)
        match = next(
            (
                promise
                for promise in promises
                if needle in promise.id and promise.state is PromiseState.PENDING
            ),
            None,
        )
        if match is not None:
            return match
        time.sleep(0.1)
    raise TimeoutError(f"run {run_id!r} did not expose pending promise {label!r}")
