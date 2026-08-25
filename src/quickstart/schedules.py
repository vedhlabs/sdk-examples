import ogha

from example_support.store import stable_id, store


@ogha.step(retry=ogha.RetryPolicy(max_attempts=3), timeout=30)
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
    catch_up_window_ms=6 * 60 * 60 * 1000,
    revision=1,
)
@ogha.workflow(name="quickstart.daily-report", target="python://quickstart")
async def daily_report(ctx, request: dict) -> dict:
    occurrence = ogha.scheduled_time(ctx).isoformat()
    report = await ctx.call(build_report, request["report"], occurrence)
    ctx.emit("ReportBuilt", report)
    return report

