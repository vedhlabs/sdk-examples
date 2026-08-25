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
    assert daily_report.__ogha_spec__.schedule.schedule_id == "quickstart.daily-report"
    assert reports_daily.__ogha_spec__.schedule.schedule_id == "reports.daily-kpis"
    assert rebalance_day.__ogha_spec__.schedule.schedule_id == "trading.rebalance-day"
    assert risk_score.__ogha_step_name__ == "risk.score"

