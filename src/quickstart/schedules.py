import aga_runtime as aga

from example_support.store import stable_id, store
from quickstart.app import app


@app.step(retry=aga.RetryPolicy(max_attempts=3), timeout=30)
def build_report(report: str, occurrence: str) -> dict:
    key = f"{report}:{occurrence}"
    return store.once(
        "quickstart.reports.build",
        key,
        lambda: {
            "report_id": stable_id("report", key),
            "report": report,
            "occurrence": occurrence,
        },
    )


@app.schedule(
    "0 6 * * *",
    schedule_id="quickstart.daily-report",
    input={"report": "daily-kpis"},
    overlap=aga.OVERLAP_SKIP,
    revision=1,
)
@app.workflow(name="quickstart.daily-report")
async def daily_report(request: dict) -> dict:
    scheduled_time = aga.info().scheduled_time
    assert scheduled_time is not None
    occurrence = scheduled_time.isoformat()
    report = await build_report(request["report"], occurrence)
    aga.event("ReportBuilt", report)
    return report
