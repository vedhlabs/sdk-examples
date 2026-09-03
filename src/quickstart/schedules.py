import ogha

from example_support.store import stable_id, store
from quickstart.app import app


@app.step(retry=ogha.RetryPolicy(max_attempts=3), timeout=30)
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


@ogha.scheduled(
    "0 6 * * *",
    schedule_id="quickstart.daily-report",
    context={"report": "daily-kpis"},
    overlap=ogha.OVERLAP_SKIP,
    revision=1,
)
@app.workflow(name="quickstart.daily-report")
async def daily_report(request: dict) -> dict:
    occurrence = ogha.scheduled_time().isoformat()
    report = await build_report(request["report"], occurrence)
    ogha.event("ReportBuilt", report)
    return report
