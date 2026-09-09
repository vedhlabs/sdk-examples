from __future__ import annotations

import json
import os
from typing import Any
from urllib import request

import aga_runtime as aga
from aga_runtime.client import Client


def connect(default_namespace: str = "default") -> Client:
    """Build the raw client used only at an operator or App-support boundary."""
    return Client(
        os.getenv("AGA_URL", "http://localhost:8080"),
        namespace=os.getenv("AGA_NAMESPACE", default_namespace),
    )


def create_namespace(name: str) -> str:
    """Provision an isolated Namespace for an end-to-end test and return its ID.

    Namespace creation is an administrative operation. Local smoke stacks run
    with authentication disabled; an authenticated stack must supply an admin
    credential through ``AGA_API_KEY``.
    """
    base_url = os.getenv("AGA_URL", "http://localhost:8080").rstrip("/")
    payload = json.dumps({"name": name}).encode()
    headers = {"Content-Type": "application/json"}
    if api_key := os.getenv("AGA_API_KEY"):
        headers["Authorization"] = f"Bearer {api_key}"
    call = request.Request(
        f"{base_url}/api/namespaces",
        data=payload,
        headers=headers,
        method="POST",
    )
    with request.urlopen(call, timeout=10) as response:  # noqa: S310 - configured Aga URL
        body = json.load(response)
    namespace_id = str(body["namespace"]["id"])
    if not namespace_id:
        raise RuntimeError("Aga returned an empty Namespace ID")
    return namespace_id


def create_app(
    name: str,
    *,
    default_namespace: str = "default",
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
