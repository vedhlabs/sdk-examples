import ogha

from checkout.workflows import charge_order, create_shipment
from checkout.workflows import checkout as compact_checkout
from ecommerce.workflow import checkout as ecommerce_checkout
from lending.workflows import application, month_end, statement
from primitives.methods import methods_tour, risk_score
from quickstart.schedules import daily_report
from quickstart.workflows import checkout as quickstart_checkout
from reports.workflows import reports_daily
from trading.workflows import rebalance_day, trading_rebalance


def test_documented_workflow_names_and_targets_are_registered():
    expected = {
        quickstart_checkout: ("quickstart.checkout", "python://quickstart"),
        compact_checkout: ("checkout", "python://checkout"),
        reports_daily: ("reports.daily", "python://reports"),
        ecommerce_checkout: ("ecommerce.checkout", "python://ecommerce"),
        application: ("lending.application", "python://lending"),
        statement: ("lending.statement", "python://lending"),
        month_end: ("lending.month_end", "python://lending"),
        trading_rebalance: ("trading.rebalance", "python://trading"),
        rebalance_day: ("trading.rebalance-day", "python://trading"),
        methods_tour: ("primitives.tour", "python://primitives"),
    }
    for function, (name, target) in expected.items():
        spec = function.__ogha_spec__
        assert spec.name == name
        assert spec.target == target


def test_fanout_workflows_are_distributed():
    assert ecommerce_checkout.__ogha_spec__.execution == "async_distributed"
    assert application.__ogha_spec__.execution == "async_distributed"
    assert trading_rebalance.__ogha_spec__.execution == "async_distributed"
    assert methods_tour.__ogha_spec__.execution == "async_distributed"


def test_schedules_and_rpc_method_are_declared():
    schedules = {
        daily_report: "quickstart.daily-report",
        reports_daily: "reports.daily-kpis",
        rebalance_day: "trading.rebalance-day",
    }
    for workflow, schedule_id in schedules.items():
        schedule = workflow.__ogha_spec__.schedule
        assert schedule.schedule_id == schedule_id
        assert not (
            schedule.overlap == ogha.OVERLAP_SKIP and schedule.catch_up_window_ms > 0
        ), "OVERLAP_SKIP and catch-up are mutually exclusive"
    assert risk_score.__ogha_step_name__ == "risk.score"


def test_compact_checkout_places_the_pivot_at_payment():
    assert charge_order.__ogha_spec__.pivot is True
    assert create_shipment.__ogha_spec__.pivot is False
