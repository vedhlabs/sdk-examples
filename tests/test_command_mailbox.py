import asyncio

import aga_runtime as aga
import pytest

from agent_pattern import command_session
from agent_pattern.control_plane import ControlPlane, ControlPlaneError


def _command(revision: int, kind: str, payload=None) -> aga.Command:
    return aga.Command(
        session_id="conversation-42",
        command_id=f"command-{revision}",
        revision=revision,
        kind=kind,
        payload=payload,
        actor_id="operator-1",
        created_at=revision,
        delivered_at=revision + 1,
    )


def test_mailbox_session_handles_ordered_commands_and_stops(monkeypatch):
    commands = iter(
        [
            _command(1, "message", {"text": "check the application"}),
            _command(2, "stop"),
        ]
    )
    events = []

    async def receive(*, timeout):
        assert timeout == 30.0
        return next(commands)

    async def handle(command_id, kind, payload):
        return {"command_id": command_id, "kind": kind, "status": "answered"}

    monkeypatch.setattr(command_session.app, "command", receive)
    monkeypatch.setattr(command_session, "handle_command", handle)
    monkeypatch.setattr(
        command_session.app,
        "event",
        lambda name, value: events.append((name, value)),
    )

    result = asyncio.run(
        command_session.command_session.__wrapped__(
            {
                "handled": 0,
                "generation": 1,
                "commands_per_generation": 2,
                "command_timeout": 30,
                "recent_results": [],
            }
        )
    )

    assert result["handled"] == 1
    assert result["generations"] == 1
    assert result["stop_revision"] == 2
    assert [event[0] for event in events] == [
        "agent.command.completed",
        "agent.session.stopped",
    ]


def test_command_work_is_bounded(monkeypatch):
    sleeps = []
    monkeypatch.setattr(command_session.time, "sleep", sleeps.append)

    result = command_session.handle_command.__wrapped__(
        "command-1", "message", {"text": "hello", "work_ms": 125}
    )

    assert result["status"] == "answered"
    assert sleeps == [0.125]


@pytest.mark.parametrize("work_ms", [-1, 1001, True, 1.5])
def test_command_work_refuses_unbounded_delay(work_ms):
    with pytest.raises(ValueError, match="between 0 and 1000"):
        command_session.handle_command.__wrapped__(
            "command-1", "message", {"text": "hello", "work_ms": work_ms}
        )


def test_mailbox_session_continues_with_bounded_committed_state(monkeypatch):
    class Continued(Exception):
        pass

    captured = {}

    async def receive(*, timeout):
        assert timeout == 60.0
        return _command(8, "message", {"text": "continue"})

    async def handle(command_id, kind, payload):
        return {"command_id": command_id, "kind": kind, "status": "answered"}

    def continue_as_new(workflow, state):
        captured.update(workflow=workflow, state=state)
        raise Continued

    monkeypatch.setattr(command_session.app, "command", receive)
    monkeypatch.setattr(command_session, "handle_command", handle)
    monkeypatch.setattr(command_session.app, "event", lambda *_args: None)
    monkeypatch.setattr(command_session.app, "continue_as_new", continue_as_new)

    with pytest.raises(Continued):
        asyncio.run(
            command_session.command_session.__wrapped__(
                {
                    "handled": 7,
                    "generation": 3,
                    "commands_per_generation": 1,
                    "command_timeout": 60,
                    "recent_results": [{"revision": index} for index in range(9)],
                }
            )
        )

    assert captured["workflow"] is command_session.command_session
    assert captured["state"]["handled"] == 8
    assert captured["state"]["generation"] == 4
    assert len(captured["state"]["recent_results"]) == command_session.RECENT_RESULT_LIMIT
    assert captured["state"]["recent_results"][-1]["revision"] == 8


def test_control_plane_rereads_revision_once_after_concurrent_writer(monkeypatch):
    client = ControlPlane(url="http://aga", namespace="demo", api_key="secret")
    calls = []

    def call(method, path, body=None):
        calls.append((method, path, body))
        if method == "GET":
            revision = 4 if len([item for item in calls if item[0] == "GET"]) == 1 else 5
            return {"current_revision": revision}
        if body["expected_revision"] == 4:
            raise ControlPlaneError(409, "revision conflict")
        return {"command": {"revision": 6, "command_id": body["command_id"]}}

    monkeypatch.setattr(client, "_call", call)
    response = client.send_command(
        "conversation-42",
        command_id="stable-command",
        kind="message",
        payload={"text": "hello"},
    )

    assert response["command"]["revision"] == 6
    posts = [item[2] for item in calls if item[0] == "POST"]
    assert [body["expected_revision"] for body in posts] == [4, 5]
    assert all(body["command_id"] == "stable-command" for body in posts)
    assert all("actor_id" not in body for body in posts)


def test_control_plane_updates_desired_state_with_registry_revision(monkeypatch):
    client = ControlPlane(url="http://aga", namespace="demo")
    calls = []

    def call(method, path, body=None):
        calls.append((method, path, body))
        if method == "GET":
            return {
                "agents": [
                    {
                        "deployment": {
                            "agent_id": "agent-pattern",
                            "display_name": "old",
                            "revision": 7,
                        }
                    }
                ]
            }
        return {"agent": {"agent_id": "agent-pattern", "revision": 8}}

    monkeypatch.setattr(client, "_call", call)
    response = client.register_agent(
        agent_id="agent-pattern",
        display_name="Mailbox agent",
        target="python://agent-pattern",
        release="v1",
        manifest_digest="sha256:v1",
        desired_replicas=2,
        concurrency=4,
    )

    assert response["agent"]["revision"] == 8
    patch = calls[-1]
    assert patch[0:2] == ("PATCH", "/api/agents/agent-pattern")
    assert patch[2]["expected_revision"] == 7


def test_control_plane_pages_sessions_and_reads_runtime_facts(monkeypatch):
    client = ControlPlane(url="http://aga", namespace="demo")
    calls = []

    def call(method, path, body=None):
        calls.append((method, path, body))
        return {}

    monkeypatch.setattr(client, "_call", call)
    client.sessions(agent_id="fleet agent", cursor="session/200", limit=200)
    client.workers()
    client.metrics()

    assert calls == [
        (
            "GET",
            "/api/sessions?limit=200&agent_id=fleet%20agent&cursor=session%2F200",
            None,
        ),
        ("GET", "/api/workers", None),
        ("GET", "/api/metrics", None),
    ]


@pytest.mark.parametrize("limit", [0, 201, True, 1.5])
def test_control_plane_refuses_invalid_session_page_size(limit):
    with pytest.raises(ValueError, match="between 1 and 200"):
        ControlPlane(url="http://aga", namespace="demo").sessions(limit=limit)
