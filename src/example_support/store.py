from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

T = TypeVar("T")


def stable_id(prefix: str, key: str) -> str:
    digest = hashlib.sha256(key.encode()).hexdigest()[:16]
    return f"{prefix}_{digest}"


class ExampleStore:
    """Tiny durable stand-in for external providers used by the local examples.

    It is intentionally separate from Ogha's PostgreSQL state. That preserves the
    real distributed-systems boundary: an Ogha step may be retried after this
    provider committed, so provider-side idempotency must return the first result.
    """

    def __init__(self, path: str | None = None) -> None:
        configured = path or os.getenv("OGHA_EXAMPLE_STATE", ".state/examples.sqlite3")
        self.path = Path(configured)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.execute("PRAGMA busy_timeout=10000")
        return db

    def _initialize(self) -> None:
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS effects (
                    scope TEXT NOT NULL,
                    effect_key TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    calls INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY (scope, effect_key)
                )
                """
            )
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS state (
                    scope TEXT NOT NULL,
                    state_key TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    PRIMARY KEY (scope, state_key)
                )
                """
            )

    def once(self, scope: str, key: str, create: Callable[[], T]) -> T:
        """Return the first committed result for `(scope, key)` on every retry."""
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT value_json FROM effects WHERE scope = ? AND effect_key = ?",
                (scope, key),
            ).fetchone()
            if row is not None:
                db.execute(
                    "UPDATE effects SET calls = calls + 1 WHERE scope = ? AND effect_key = ?",
                    (scope, key),
                )
                return json.loads(row[0])
            value = create()
            db.execute(
                "INSERT INTO effects(scope, effect_key, value_json) VALUES (?, ?, ?)",
                (scope, key, json.dumps(value, sort_keys=True)),
            )
            return value

    def get(self, scope: str, key: str, default: T | None = None) -> Any | T | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT value_json FROM state WHERE scope = ? AND state_key = ?",
                (scope, key),
            ).fetchone()
        return json.loads(row[0]) if row is not None else default

    def set(self, scope: str, key: str, value: Any) -> Any:
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO state(scope, state_key, value_json) VALUES (?, ?, ?)
                ON CONFLICT(scope, state_key) DO UPDATE SET value_json = excluded.value_json
                """,
                (scope, key, json.dumps(value, sort_keys=True)),
            )
        return value

    def effect_calls(self, scope: str, key: str) -> int:
        with self._connect() as db:
            row = db.execute(
                "SELECT calls FROM effects WHERE scope = ? AND effect_key = ?",
                (scope, key),
            ).fetchone()
        return int(row[0]) if row is not None else 0

    def clear(self) -> None:
        with self._connect() as db:
            db.execute("DELETE FROM effects")
            db.execute("DELETE FROM state")


store = ExampleStore()
