from __future__ import annotations

import json
import os
from typing import Any

import aga_runtime as aga
from aga_runtime.client import Client


def connect(default_namespace: str = "default") -> Client:
    """Build the raw client used only at an operator or App-support boundary."""
    return Client(
        os.getenv("AGA_URL", "http://localhost:8080"),
        tenant=os.getenv("AGA_TENANT", "default"),
        namespace=os.getenv("AGA_NAMESPACE", default_namespace),
    )


def create_app(
    name: str,
    *,
    default_namespace: str,
    concurrency: int = 4,
    lease_ttl_ms: int = 30_000,
) -> aga.App:
    """Create one owner for registration, connection, and worker lifecycle."""
    return aga.App(
        name,
        namespace=os.getenv("AGA_NAMESPACE", default_namespace),
        concurrency=concurrency,
        lease_ttl_ms=lease_ttl_ms,
    )


def decode_output(value: bytes) -> Any:
    if not value:
        return None
    return json.loads(value.decode())
