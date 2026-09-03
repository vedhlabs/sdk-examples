from quickstart import crash_workflow, schedules, workflows  # noqa: F401
from quickstart.app import app


def main() -> None:
    app.serve()


if __name__ == "__main__":
    main()
