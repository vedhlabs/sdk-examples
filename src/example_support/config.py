from __future__ import annotations

import json
import os
from typing import Any

import ogha


def connect(default_namespace: str = "default") -> ogha.Client:
    """Build one consistently configured client for workers and operator tools."""
    return ogha.connect(
        os.getenv("OGHA_URL", "http://localhost:8080"),
        namespace=os.getenv("OGHA_NAMESPACE", default_namespace),
    )


def decode_output(value: bytes) -> Any:
    if not value:
        return None
    return json.loads(value.decode())

