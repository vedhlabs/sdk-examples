_PORTFOLIOS = {
    "growth": {
        "AAPL": {"weight": "0.55", "reference_price": "200"},
        "MSFT": {"weight": "0.45", "reference_price": "400"},
    },
    "income": {
        "AAPL": {"weight": "0.35", "reference_price": "200"},
        "MSFT": {"weight": "0.65", "reference_price": "400"},
    },
}


def target_weights(portfolio: str, positions: list[dict], account: dict) -> dict:
    del positions, account
    try:
        return _PORTFOLIOS[portfolio]
    except KeyError as exc:
        raise ValueError(f"unknown portfolio: {portfolio}") from exc

