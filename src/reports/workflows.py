import ogha

from example_support.store import stable_id, store


@ogha.step(retry=ogha.RetryPolicy(max_attempts=3), timeout=45)
def render_report(report: str, occurrence: str) -> dict:
    key = f"{report}:{occurrence}"
    return store.once(
        "reports.render",
        key,
        lambda: {"id": stable_id("report", key), "report": report, "at": occurrence},
    )


@ogha.scheduled(
    "0 6 * * *",
    schedule_id="reports.daily-kpis",
    context={"report": "daily-kpis"},
    overlap=ogha.OVERLAP_SKIP,
    catch_up_window_ms=6 * 60 * 60 * 1000,
    revision=1,
)
@ogha.workflow(name="reports.daily", target="python://reports")
async def reports_daily(ctx, request: dict) -> dict:
    occurrence = ogha.scheduled_time(ctx).isoformat()
    return await ctx.call(render_report, request["report"], occurrence)

