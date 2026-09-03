from quickstart import crash_workflow  # noqa: F401
from quickstart.app import app


def main() -> None:
    app.serve()


if __name__ == "__main__":
    main()
