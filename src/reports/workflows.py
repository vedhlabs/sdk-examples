import aga_runtime as aga

from example_support.store import stable_id, store
from reports.app import app


@app.step(retry=aga.RetryPolicy(max_attempts=3), timeout=45)
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
    overlap=aga.OVERLAP_SKIP,
    revision=1,
)
@app.workflow(name="reports.daily")
async def reports_daily(request: dict) -> dict:
    scheduled_time = aga.info().scheduled_time
    assert scheduled_time is not None
    occurrence = scheduled_time.isoformat()
    return await render_report(request["report"], occurrence)
