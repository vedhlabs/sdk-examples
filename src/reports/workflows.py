import ogha

from example_support.store import stable_id, store
from reports.app import app


@app.step(retry=ogha.RetryPolicy(max_attempts=3), timeout=45)
def render_report(report: str, occurrence: str) -> dict:
    key = f"{report}:{occurrence}"
    return store.once(
        "reports.render",
        key,
        lambda: {"id": stable_id("report", key), "report": report, "at": occurrence},
    )


@app.schedule(
    "0 6 * * *",
    schedule_id="reports.daily-kpis",
    input={"report": "daily-kpis"},
    overlap=ogha.OVERLAP_SKIP,
    revision=1,
)
@app.workflow(name="reports.daily")
async def reports_daily(request: dict) -> dict:
    occurrence = ogha.scheduled_time().isoformat()
    return await render_report(request["report"], occurrence)
