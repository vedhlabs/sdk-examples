"""Qualify a large parked-agent fleet against an authenticated Aga deployment."""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
import time
import traceback
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = Path(__file__).with_name("agent_fleet_policy.json")
TARGET = "python://agent-pattern"


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(0, math.ceil(fraction * len(ordered)) - 1)
    return ordered[rank]


def process_usage(pid: int) -> tuple[float, int]:
    result = subprocess.run(
        ["ps", "-o", "time=,rss=", "-p", str(pid)],
        check=True,
        capture_output=True,
        text=True,
    )
    fields = result.stdout.strip().split()
    if len(fields) != 2:
        raise RuntimeError(f"unexpected ps output for worker {pid}: {result.stdout!r}")
    return _cpu_seconds(fields[0]), int(fields[1]) * 1024


def _cpu_seconds(value: str) -> float:
    days = 0
    if "-" in value:
        day_text, value = value.split("-", 1)
        days = int(day_text)
    parts = value.split(":")
    if len(parts) == 2:
        hours, minutes, seconds = 0, int(parts[0]), float(parts[1])
    elif len(parts) == 3:
        hours, minutes, seconds = int(parts[0]), int(parts[1]), float(parts[2])
    else:
        raise ValueError(f"unrecognized process CPU time: {value!r}")
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def evaluate(policy: dict[str, Any], report: dict[str, Any]) -> list[str]:
    failures: list[str] = []

    def minimum(field: str, actual: float, label: str) -> None:
        expected = float(policy[field])
        if actual < expected:
            failures.append(f"{label} {actual:g} is below {expected:g}")

    def maximum(field: str, actual: float, label: str) -> None:
        expected = float(policy[field])
        if actual > expected:
            failures.append(f"{label} {actual:g} exceeds {expected:g}")

    minimum("minimumSessions", report["sessions"], "sessions")
    minimum("minimumWorkers", report["workers"], "workers")
    maximum("maximumProvisionSeconds", report["provision_seconds"], "provision seconds")
    maximum("maximumSubmitP99Ms", report["submit_ms"]["p99"], "submit p99 ms")
    maximum("maximumSessionPageP99Ms", report["session_page_ms"]["p99"], "session page p99 ms")
    maximum(
        "maximumIdleWorkerCpuPercent", report["idle_worker_cpu_percent"], "idle worker CPU percent"
    )
    maximum("maximumWorkerRssBytes", report["worker_rss_bytes"]["max"], "worker RSS bytes")
    maximum(
        "maximumCommandProcessingP99Ms",
        report["command_processing_ms"]["p99"],
        "command processing p99 ms",
    )
    maximum("maximumDrainSeconds", report["drain_seconds"], "drain seconds")
    maximum("maximumFailedRuns", report["failed_runs"], "failed runs")
    if report["completed_runs"] != report["sessions"]:
        completed = report["completed_runs"]
        failures.append(f"completed runs {completed} does not match sessions {report['sessions']}")
    if report["delivered_messages"] != report["sessions"]:
        delivered = report["delivered_messages"]
        failures.append(
            f"delivered messages {delivered} does not match sessions {report['sessions']}"
        )
    if report["worker_replacements"] < 1:
        failures.append("no worker replacement was observed")
    return failures


def summary(values: list[float]) -> dict[str, float]:
    return {
        "count": len(values),
        "p50": round(percentile(values, 0.50), 3),
        "p95": round(percentile(values, 0.95), 3),
        "p99": round(percentile(values, 0.99), 3),
        "max": round(max(values, default=0.0), 3),
    }


class FleetHarness:
    def __init__(self, policy: dict[str, Any], sessions: int, output: Path):
        self.policy = policy
        self.sessions = sessions
        self.output = output
        self.prefix = f"fleet-{uuid.uuid4().hex[:10]}-"
        self.processes: list[subprocess.Popen[bytes]] = []
        self.handles: list[Any] = []
        self.session_ids: list[str] = []
        self.page_latencies: list[float] = []
        self.log_files: list[Any] = []
        self.killed_worker_pid: int | None = None
        self.replacement_worker_pid: int | None = None

    def launch_worker(self) -> subprocess.Popen[bytes]:
        log = open(self.output / f"worker-{len(self.log_files) + 1}.log", "wb")  # noqa: SIM115
        self.log_files.append(log)
        process = subprocess.Popen(
            [sys.executable, "-m", "agent_pattern.worker"],
            stdout=log,
            stderr=subprocess.STDOUT,
            env=os.environ.copy(),
        )
        self.processes.append(process)
        return process

    def hard_replace_worker(self, control: Any) -> None:
        child_by_pid = {
            process.pid: process for process in self.processes if process.poll() is None
        }

        def busy_child() -> subprocess.Popen[bytes] | None:
            for worker in control.workers()["workers"]:
                if TARGET not in worker["targets"] or int(worker["in_flight"]) < 1:
                    continue
                process = child_by_pid.get(int(worker["pid"]))
                if process is not None:
                    return process
            return None

        victim = self.wait_for("an in-flight agent worker", busy_child, 30)
        self.killed_worker_pid = victim.pid
        victim.kill()
        victim.wait(timeout=10)
        replacement = self.launch_worker()
        self.replacement_worker_pid = replacement.pid

        def replacement_online() -> bool:
            return any(
                TARGET in worker["targets"]
                and worker["state"] == "active"
                and worker["pid"] == str(replacement.pid)
                for worker in control.workers()["workers"]
            )

        self.wait_for("replacement agent worker", replacement_online, 60)

    def stop_workers(self) -> None:
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
        for process in self.processes:
            if process.poll() is None:
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
        for log in self.log_files:
            log.close()

    def sessions_page(self, control: Any) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        cursor = ""
        while True:
            started = time.monotonic()
            page = control.sessions(agent_id="agent-pattern", cursor=cursor, limit=200)
            self.page_latencies.append((time.monotonic() - started) * 1000)
            rows.extend(
                session
                for session in page["sessions"]
                if session["session_id"].startswith(self.prefix)
            )
            if not page["has_more"]:
                return rows
            next_cursor = str(page["next_cursor"])
            if not next_cursor or next_cursor == cursor:
                raise RuntimeError("session pagination did not advance")
            cursor = next_cursor

    def wait_for(self, label: str, predicate: Callable[[], Any], timeout: float) -> Any:
        deadline = time.monotonic() + timeout
        last: Any = None
        while time.monotonic() < deadline:
            last = predicate()
            if last:
                return last
            time.sleep(0.25)
        raise TimeoutError(f"timed out waiting for {label}; last={last!r}")

    def run(self) -> dict[str, Any]:
        from agent_pattern.app import app
        from agent_pattern.command_session import command_session
        from agent_pattern.control_plane import ControlPlane

        worker_key = os.environ["AGA_API_KEY"]
        admin_key = os.environ["AGA_ADMIN_KEY"]
        control = ControlPlane(api_key=worker_key)
        admin = ControlPlane(api_key=admin_key)
        workers = int(self.policy["minimumWorkers"])
        release = os.environ.setdefault("AGA_RELEASE", "fleet-qualification-v1")
        manifest = os.environ.setdefault("AGA_MANIFEST_DIGEST", "sha256:fleet-qualification-v1")
        admin.register_agent(
            agent_id="agent-pattern",
            display_name="Fleet qualification agent",
            target=TARGET,
            release=release,
            manifest_digest=manifest,
            desired_replicas=workers,
            concurrency=4,
        )
        for _ in range(workers):
            self.launch_worker()

        def online_workers() -> list[dict[str, Any]]:
            return [
                worker
                for worker in control.workers()["workers"]
                if TARGET in worker["targets"] and worker["state"] == "active"
            ]

        self.wait_for("agent workers", lambda: len(online_workers()) >= workers, 60)
        submit_ms: list[float] = []
        provision_started = time.monotonic()
        for index in range(self.sessions):
            session_id = f"{self.prefix}{index:05d}"
            run_id = f"fleet-run-{uuid.uuid4().hex[:18]}"
            started = time.monotonic()
            handle = app.start(
                command_session.options(run_id=run_id, session_id=session_id, timeout=7200),
                {
                    "handled": 0,
                    "generation": 1,
                    "commands_per_generation": 1,
                    "command_timeout": 7200,
                    "recent_results": [],
                },
            )
            submit_ms.append((time.monotonic() - started) * 1000)
            self.handles.append(handle)
            self.session_ids.append(session_id)

        def parked() -> list[dict[str, Any]] | None:
            sessions = self.sessions_page(control)
            if len(sessions) != self.sessions or any(
                row["run_state"] != "running" for row in sessions
            ):
                return None
            metrics = control.metrics()
            if metrics["backlog"]["tasks_pending"] or metrics["workers"]["in_flight"]:
                return None
            return sessions

        parked_sessions = self.wait_for(
            "all sessions to park",
            parked,
            float(self.policy["maximumProvisionSeconds"]),
        )
        provision_seconds = time.monotonic() - provision_started

        live_processes = [process for process in self.processes if process.poll() is None]
        before = {process.pid: process_usage(process.pid) for process in live_processes}
        idle_seconds = float(self.policy["idleObservationSeconds"])
        time.sleep(idle_seconds)
        after = {process.pid: process_usage(process.pid) for process in live_processes}
        cpu_delta = sum(after[pid][0] - before[pid][0] for pid in after)
        idle_cpu = max(0.0, cpu_delta / idle_seconds * 100)
        rss_values = [after[pid][1] for pid in after]

        message_created_at: dict[str, int] = {}
        for index, session_id in enumerate(self.session_ids):
            response = control.send_command(
                session_id,
                command_id=f"message-{index}",
                kind="message",
                payload={"text": f"qualify session {index}", "work_ms": 100},
            )
            message_created_at[session_id] = int(response["command"]["created_at"])
            if index + 1 == max(1, self.sessions // 2):
                self.hard_replace_worker(control)

        def messages_delivered() -> list[dict[str, Any]] | None:
            sessions = self.sessions_page(control)
            if len(sessions) != self.sessions:
                return None
            if any(row["delivered"] < 1 or row["generation"] < 2 for row in sessions):
                return None
            if any(row["run_state"] != "running" for row in sessions):
                return None
            return sessions

        continued_sessions = self.wait_for(
            "message delivery and continuation", messages_delivered, 180
        )
        processing_ms = [
            (int(session["last_activity_at"]) - message_created_at[session["session_id"]]) / 1000
            for session in continued_sessions
        ]

        def command_latency(session_id: str) -> float:
            commands = control.session_commands(session_id)["commands"]
            message = next(command for command in commands if command["kind"] == "message")
            if message["state"] != "delivered" or message["delivered_at"] is None:
                raise RuntimeError(f"message for {session_id} was not delivered")
            return (int(message["delivered_at"]) - int(message["created_at"])) / 1000

        with ThreadPoolExecutor(max_workers=32) as pool:
            delivery_ms = list(pool.map(command_latency, self.session_ids))

        drain_started = time.monotonic()
        for index, session_id in enumerate(self.session_ids):
            control.send_command(
                session_id,
                command_id=f"stop-{index}",
                kind="stop",
                payload=None,
            )

        def completed() -> list[dict[str, Any]] | None:
            sessions = self.sessions_page(control)
            if len(sessions) != self.sessions:
                return None
            if any(row["run_state"] not in {"completed", "failed", "canceled"} for row in sessions):
                return None
            return sessions

        final_sessions = self.wait_for(
            "all sessions to drain",
            completed,
            float(self.policy["maximumDrainSeconds"]),
        )
        drain_seconds = time.monotonic() - drain_started
        completed_count = sum(row["run_state"] == "completed" for row in final_sessions)
        failed_count = sum(row["run_state"] == "failed" for row in final_sessions)
        if completed_count == self.sessions:
            for handle in self.handles:
                result = handle.result(timeout=10)
                if result["handled"] != 1 or result["generations"] != 2:
                    raise RuntimeError(f"unexpected terminal session result: {result!r}")

        app.close()
        return {
            "sessions": len(parked_sessions),
            "workers": workers,
            "worker_replacements": 1,
            "killed_worker_pid": self.killed_worker_pid,
            "replacement_worker_pid": self.replacement_worker_pid,
            "provision_seconds": round(provision_seconds, 3),
            "submit_ms": summary(submit_ms),
            "session_page_ms": summary(self.page_latencies),
            "idle_observation_seconds": idle_seconds,
            "idle_worker_cpu_percent": round(idle_cpu, 3),
            "worker_rss_bytes": {
                "max": max(rss_values, default=0),
                "total": sum(rss_values),
            },
            "message_delivery_ms": summary(delivery_ms),
            "command_processing_ms": summary(processing_ms),
            "delivered_messages": len(delivery_ms),
            "drain_seconds": round(drain_seconds, 3),
            "completed_runs": completed_count,
            "failed_runs": failed_count,
            "final_metrics": control.metrics(),
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--sessions", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    sessions = args.sessions or int(policy["minimumSessions"])
    output = args.output or Path(tempfile.mkdtemp(prefix="aga-agent-fleet-"))
    output.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "schema": "aga-agent-fleet-report-v1",
        "policy": policy["name"],
        "started_at": int(time.time()),
        "evidence_grade": "insufficient",
    }
    harness = FleetHarness(policy, sessions, output)
    try:
        report.update(harness.run())
        report["failures"] = evaluate(policy, report)
        if not report["failures"]:
            report["evidence_grade"] = "local-large-fleet"
    except BaseException as exc:
        report["failures"] = [f"harness failed: {type(exc).__name__}: {exc}"]
        (output / "traceback.txt").write_text(traceback.format_exc(), encoding="utf-8")
    finally:
        harness.stop_workers()
        report["finished_at"] = int(time.time())
        (output / "fleet.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"fleet evidence: {output}")
    if report["failures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
