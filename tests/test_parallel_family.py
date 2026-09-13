import asyncio

from primitives import parallel_family

APPLICATION = {"application_id": "KYC-42", "applicant": "Demo Applicant"}


def test_given_a_check_when_it_runs_then_its_observed_duration_is_returned(monkeypatch):
    sleeps = []
    monkeypatch.setattr(parallel_family.random, "uniform", lambda _low, _high: 2.5)
    monkeypatch.setattr(parallel_family.time, "sleep", sleeps.append)

    result = parallel_family.verify_pan.__wrapped__(APPLICATION)

    assert sleeps == [2.5]
    assert result == {
        "application_id": "KYC-42",
        "check": "PAN verification",
        "delay_seconds": 2.5,
        "status": "verified",
    }


def test_given_three_children_when_parent_runs_then_all_start_before_join(monkeypatch):
    started = []
    handles = [object(), object(), object()]

    def start(workflow, application):
        assert application == APPLICATION
        started.append(workflow)
        return handles[len(started) - 1]

    async def join(*received):
        assert started == [
            parallel_family.identity_checks,
            parallel_family.employment_checks,
            parallel_family.financial_checks,
        ]
        assert list(received) == handles
        return [
            {"group": "identity"},
            {"group": "employment"},
            {"group": "financial"},
        ]

    monkeypatch.setattr(parallel_family.app, "start", start)
    monkeypatch.setattr(parallel_family.app, "join", join)

    result = asyncio.run(parallel_family.parallel_family_root.__wrapped__(APPLICATION))

    assert result["decision"] == "approved"
    assert [child["group"] for child in result["children"]] == [
        "identity",
        "employment",
        "financial",
    ]

