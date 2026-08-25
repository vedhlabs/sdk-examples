from trading.domain import plan_orders, reconciliation


def test_plan_ignores_positions_inside_drift_band():
    targets = {"AAPL": {"weight": "0.50", "reference_price": "200"}}
    positions = [{"symbol": "AAPL", "market_value": "51000", "current_price": "200"}]

    plan = plan_orders(targets, positions, {"portfolio_value": "100000"})

    assert plan["sells"] == []
    assert plan["buys"] == []


def test_plan_orders_sells_before_buys_and_uses_decimal_strings():
    targets = {
        "AAPL": {"weight": "0.30", "reference_price": "200"},
        "MSFT": {"weight": "0.70", "reference_price": "400"},
    }
    positions = [
        {"symbol": "AAPL", "market_value": "60000", "current_price": "200"},
        {"symbol": "MSFT", "market_value": "40000", "current_price": "400"},
    ]

    plan = plan_orders(targets, positions, {"portfolio_value": "100000"})

    assert [row["symbol"] for row in plan["sells"]] == ["AAPL"]
    assert [row["symbol"] for row in plan["buys"]] == ["MSFT"]
    assert plan["turnover_pct"] == "60.000000"


def test_reconciliation_reports_band_status():
    targets = {"AAPL": {"weight": "0.55"}, "MSFT": {"weight": "0.45"}}
    positions = [
        {"symbol": "AAPL", "market_value": "55000"},
        {"symbol": "MSFT", "market_value": "45000"},
    ]

    result = reconciliation(targets, positions, "100000")

    assert result["within_band"] is True
    assert result["post_drift_pct"] == {"AAPL": "0.00", "MSFT": "0.00"}
