import asyncio

import pytest

from quickstart import kyc_parallel

APPLICATION = {"application_id": "loan-1", "applicant": "Demo Applicant"}


@pytest.mark.parametrize(
    ("step", "check", "field", "value"),
    [
        (kyc_parallel.pan_verification, "PAN verification", "status", "verified"),
        (kyc_parallel.employment_check, "Employment check", "status", "active"),
        (kyc_parallel.bureau_pull, "Credit bureau pull", "score", 762),
        (kyc_parallel.sanctions_screening, "Sanctions screening", "matches", 0),
        (
            kyc_parallel.bank_account_verification,
            "Bank account verification",
            "status",
            "verified",
        ),
    ],
)
def test_given_kyc_step_when_it_runs_then_result_identifies_check(
    monkeypatch,
    step,
    check,
    field,
    value,
):
    sleeps = []

    def random_delay(low, high):
        assert (low, high) == (2, 3)
        return 2.5

    monkeypatch.setattr(kyc_parallel.random, "uniform", random_delay)
    monkeypatch.setattr(kyc_parallel.time, "sleep", sleeps.append)

    result = step.__wrapped__(APPLICATION)

    assert result["application_id"] == "loan-1"
    assert result["check"] == check
    assert result[field] == value
    assert result["delay_seconds"] == 2.5
    assert sleeps == [2.5]


def test_given_five_checks_when_workflow_runs_then_all_calls_precede_join(monkeypatch):
    calls = []
    handles = [object() for _ in range(5)]
    names = [
        "pan_verification",
        "employment_check",
        "bureau_pull",
        "sanctions_screening",
        "bank_account_verification",
    ]

    for name, handle in zip(names, handles, strict=True):

        def call(application, *, _name=name, _handle=handle):
            calls.append((_name, application["application_id"]))
            return _handle

        monkeypatch.setattr(kyc_parallel, name, call)

    async def join(*submitted):
        assert list(submitted) == handles
        assert calls == [(name, "loan-1") for name in names]
        return [{"check": name} for name in names]

    monkeypatch.setattr(kyc_parallel.app, "join", join)
    result = asyncio.run(kyc_parallel.kyc_review.__wrapped__(APPLICATION))

    assert result["application_id"] == "loan-1"
    assert result["decision"] == "approved"
    assert result["checks"] == [{"check": name} for name in names]


def test_given_kyc_workflow_when_declared_then_placement_is_sticky():
    assert kyc_parallel.kyc_review.__aga_spec__.execution == "async_sticky"
