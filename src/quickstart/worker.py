import os

from quickstart import crash_workflow, workflows  # noqa: F401
from quickstart.app import app

if os.getenv("AGA_EXAMPLE_SCHEDULES", "1") != "0":
    from quickstart import schedules as schedules  # noqa: F401


def main() -> None:
    app.serve()


if __name__ == "__main__":
    main()
