from __future__ import annotations

import json
import os
from typing import Any

import ogha
from ogha.client import Client


def connect(default_namespace: str = "default") -> Client:
    """Build the client an App owns, or an operator boundary borrows."""
    return Client(
        os.getenv("OGHA_URL", "http://localhost:8080"),
        tenant=os.getenv("OGHA_TENANT", "default"),
        namespace=os.getenv("OGHA_NAMESPACE", default_namespace),
    )


def create_app(
    name: str,
    *,
    default_namespace: str,
    concurrency: int = 4,
    lease_ttl_ms: int = 30_000,
) -> ogha.App:
    """Create one owner for registration, connection, and worker lifecycle."""
    return ogha.App(
        name,
        client=connect(default_namespace),
        concurrency=concurrency,
        lease_ttl_ms=lease_ttl_ms,
    )


def decode_output(value: bytes) -> Any:
    if not value:
        return None
    return json.loads(value.decode())
