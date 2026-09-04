import os

from trading import steps, workflows  # noqa: F401
from trading.app import app

if os.getenv("AGA_EXAMPLE_SCHEDULES", "1") != "0":
    from trading import schedules as schedules  # noqa: F401


def main() -> None:
    app.serve()


if __name__ == "__main__":
    main()
