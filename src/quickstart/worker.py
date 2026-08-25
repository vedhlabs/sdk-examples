import ogha

from quickstart import crash_workflow, schedules, workflows  # noqa: F401
from quickstart.client import connect


def main() -> None:
    ogha.Worker(
        connect(),
        target="python://quickstart",
        concurrency=8,
        service="quickstart",
    ).run()


if __name__ == "__main__":
    main()

