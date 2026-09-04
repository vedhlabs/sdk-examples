import argparse

from quickstart.client import connect


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect or pause the quickstart schedule")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("list")
    pause = subcommands.add_parser("pause")
    pause.add_argument("schedule_id", default="quickstart.daily-report", nargs="?")
    resume = subcommands.add_parser("resume")
    resume.add_argument("schedule_id", default="quickstart.daily-report", nargs="?")
    args = parser.parse_args()

    client = connect()
    if args.command == "list":
        cursor = ""
        while True:
            page, cursor = client.list_schedules(limit=20, cursor=cursor)
            for schedule in page:
                print(
                    schedule.id,
                    schedule.cron,
                    f"revision={schedule.revision}",
                    f"paused={schedule.paused}",
                )
            if not cursor:
                break
        return

    current = client.get_schedule(args.schedule_id)
    tags = current.tags or {}
    client.update_schedule(
        current.id,
        tags.get("ogha:wf", "quickstart.daily-report"),
        schedule=current.cron,
        revision=current.revision + 1,
        target=tags.get("ogha:target", "python://quickstart"),
        input=current.param,
        timeout_ms=current.timeout_ms,
        paused=args.command == "pause",
        overlap=current.overlap,
        catch_up_window_ms=current.catch_up_window_ms,
        run_id_template=current.run_id_template,
    )
    print(f"{args.schedule_id}: {'paused' if args.command == 'pause' else 'active'}")


if __name__ == "__main__":
    main()
