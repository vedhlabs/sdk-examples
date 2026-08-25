from example_support.store import stable_id, store


def record(portfolio: str, run_tag: str, executed: dict, reconciliation: dict) -> dict:
    return store.once(
        "trading.books.record",
        run_tag,
        lambda: {
            "record_id": stable_id("book", run_tag),
            "portfolio": portfolio,
            "executed": executed,
            "reconciliation": reconciliation,
        },
    )

