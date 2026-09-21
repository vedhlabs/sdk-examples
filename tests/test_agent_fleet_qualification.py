from scripts.agent_fleet_qualification import _cpu_seconds, evaluate, percentile


def test_percentile_uses_nearest_rank():
    assert percentile([1, 2, 3, 4, 5], 0.50) == 3
    assert percentile([1, 2, 3, 4, 5], 0.99) == 5
    assert percentile([], 0.99) == 0


def test_process_cpu_time_accepts_platform_formats():
    assert _cpu_seconds("01:02.50") == 62.5
    assert _cpu_seconds("01:02:03") == 3723
    assert _cpu_seconds("1-01:02:03") == 90123


def test_fleet_report_passes_only_when_every_gate_holds():
    policy = {
        "minimumSessions": 1000,
        "minimumWorkers": 4,
        "maximumProvisionSeconds": 300,
        "maximumSubmitP99Ms": 250,
        "maximumSessionPageP99Ms": 500,
        "maximumIdleWorkerCpuPercent": 5,
        "maximumWorkerRssBytes": 128 * 1024 * 1024,
        "maximumCommandProcessingP99Ms": 120000,
        "maximumDrainSeconds": 180,
        "maximumFailedRuns": 0,
    }
    report = {
        "sessions": 1000,
        "workers": 4,
        "worker_replacements": 1,
        "provision_seconds": 120,
        "submit_ms": {"p99": 20},
        "session_page_ms": {"p99": 30},
        "idle_worker_cpu_percent": 0.5,
        "worker_rss_bytes": {"max": 30 * 1024 * 1024},
        "command_processing_ms": {"p99": 82000},
        "delivered_messages": 1000,
        "drain_seconds": 60,
        "completed_runs": 1000,
        "failed_runs": 0,
    }
    assert evaluate(policy, report) == []

    report["completed_runs"] = 999
    assert evaluate(policy, report) == ["completed runs 999 does not match sessions 1000"]
