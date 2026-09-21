"""Small operator client for the mailbox and desired fleet APIs."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib import error, parse, request


@dataclass(frozen=True)
class ControlPlaneError(RuntimeError):
    status: int
    message: str

    def __str__(self) -> str:
        return f"Aga control-plane request failed ({self.status}): {self.message}"


class ControlPlane:
    """Call authenticated, Namespace-scoped operator APIs with bounded timeouts."""

    def __init__(
        self,
        *,
        url: str | None = None,
        namespace: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self._url = (url or os.getenv("AGA_URL", "http://localhost:8080")).rstrip("/")
        self._namespace = namespace or os.getenv("AGA_NAMESPACE", "default")
        self._api_key = api_key if api_key is not None else os.getenv("AGA_API_KEY", "")

    def session_commands(self, session_id: str) -> dict[str, Any]:
        path = f"/api/sessions/{_segment(session_id)}/commands?limit=200"
        return self._call("GET", path)

    def sessions(
        self,
        *,
        agent_id: str = "",
        cursor: str = "",
        limit: int = 200,
    ) -> dict[str, Any]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 200:
            raise ValueError("session page limit must be between 1 and 200")
        query = f"?limit={limit}"
        if agent_id:
            query += "&agent_id=" + parse.quote(agent_id, safe="")
        if cursor:
            query += "&cursor=" + parse.quote(cursor, safe="")
        return self._call("GET", "/api/sessions" + query)

    def workers(self) -> dict[str, Any]:
        return self._call("GET", "/api/workers")

    def metrics(self) -> dict[str, Any]:
        return self._call("GET", "/api/metrics")

    def send_command(
        self,
        session_id: str,
        *,
        command_id: str,
        kind: str,
        payload: Any,
    ) -> dict[str, Any]:
        """Send once, rereading the revision after one concurrent-writer conflict."""
        path = f"/api/sessions/{_segment(session_id)}/commands"
        for attempt in range(2):
            current = self.session_commands(session_id)
            body = {
                "expected_revision": current["current_revision"],
                "command_id": command_id,
                "kind": kind,
                "payload": payload,
            }
            try:
                return self._call("POST", path, body)
            except ControlPlaneError as exc:
                if exc.status != 409 or attempt == 1:
                    raise
        raise AssertionError("unreachable")

    def register_agent(
        self,
        *,
        agent_id: str,
        display_name: str,
        target: str,
        release: str,
        manifest_digest: str,
        desired_replicas: int,
        concurrency: int,
        framework: str = "python",
        model: str = "",
    ) -> dict[str, Any]:
        desired = {
            "display_name": display_name,
            "description": "Mailbox-driven agent example",
            "target": target,
            "framework": framework,
            "model": model,
            "release": release,
            "manifest_digest": manifest_digest,
            "desired_replicas": desired_replicas,
            "concurrency_per_worker": concurrency,
            "state": "enabled",
        }
        try:
            page = self._call("GET", f"/api/agents/{_segment(agent_id)}")
        except ControlPlaneError as exc:
            if exc.status != 404:
                raise
            return self._call("POST", "/api/agents", {"agent_id": agent_id, **desired})

        rows = page.get("agents", [])
        if len(rows) != 1:
            raise RuntimeError(f"Aga returned {len(rows)} rows for agent {agent_id!r}")
        current = rows[0]["deployment"]
        if all(current.get(key) == value for key, value in desired.items()):
            return {"agent": current}
        return self._call(
            "PATCH",
            f"/api/agents/{_segment(agent_id)}",
            {"expected_revision": current["revision"], **desired},
        )

    def agents(self) -> dict[str, Any]:
        return self._call("GET", "/api/agents?limit=200")

    def _call(self, method: str, path: str, body: Any = None) -> dict[str, Any]:
        headers = {
            "Accept": "application/json",
            "X-Aga-Namespace": self._namespace,
        }
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body, separators=(",", ":")).encode()
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        call = request.Request(self._url + path, data=data, headers=headers, method=method)
        try:
            with request.urlopen(call, timeout=10) as response:  # noqa: S310 - configured Aga URL
                return json.load(response)
        except error.HTTPError as exc:
            try:
                response = json.loads(exc.read())
                message = str(response.get("error", exc.reason))
            except (json.JSONDecodeError, UnicodeDecodeError):
                message = str(exc.reason)
            raise ControlPlaneError(exc.code, message) from exc


def _segment(value: str) -> str:
    if not value or any(ord(character) < 32 for character in value):
        raise ValueError("path identifier must be nonempty and contain no control characters")
    return parse.quote(value, safe="")
