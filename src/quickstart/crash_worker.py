import ogha

from quickstart import crash_workflow  # noqa: F401
from quickstart.client import connect


def main() -> None:
    ogha.Worker(
        connect(),
        target="python://quickstart",
        concurrency=2,
        lease_ttl_ms=8_000,
        service="quickstart-crash",
    ).run()


if __name__ == "__main__":
    main()

