import asyncio

import pytest

from quickstart import inside_execution as lab

NAMES = ["verify_pan", "check_employment", "pull_bureau", "screen_sanctions", "verify_bank"]
APPLICANT = {"applicant_id": "DEMO-001"}


@pytest.mark.parametrize("name", NAMES)
def test_five_distinct_providers_keep_their_identity(monkeypatch, name):
    sleeps = []
    monkeypatch.setattr(lab.time, "sleep", sleeps.append)
    result = getattr(lab, name).__wrapped__(APPLICANT)
    assert result["check"] == name
    assert result["applicant_id"] == "DEMO-001"
    assert result["result"] == "demo-ok"
    assert result["finished_ns"] >= result["started_ns"]
    assert sleeps == [1.2]


@pytest.mark.parametrize("parallel", [False, True])
@pytest.mark.parametrize("workflow", [lab.sticky, lab.distributed])
def test_calls_and_awaits_have_the_documented_order(monkeypatch, parallel, workflow):
    events = []

    class ObservedHandle:
        def __init__(self, name):
            self.name = name

        def __await__(self):
            async def result():
                events.append(("await", self.name))
                return {"check": self.name}

            return result().__await__()

    for name in NAMES:

        def call(applicant, _name=name):
            assert applicant == APPLICANT
            events.append(("call", _name))
            return ObservedHandle(_name)

        monkeypatch.setattr(lab, name, call)

    async def join(*handles):
        assert events == [("call", name) for name in NAMES]
        return [await handle for handle in handles]

    monkeypatch.setattr(lab.app, "join", join)
    assert asyncio.run(workflow.__wrapped__(APPLICANT, parallel)) == [
        {"check": name} for name in NAMES
    ]
    expected = (
        ([("call", name) for name in NAMES] + [("await", name) for name in NAMES])
        if parallel
        else [(event, name) for name in NAMES for event in ["call", "await"]]
    )
    assert events == expected


def test_placement_is_independent_of_caller_waiting():
    assert lab.sticky.__aga_spec__.execution == "async_sticky"
    assert lab.distributed.__aga_spec__.execution == "async_distributed"
    args = lab.parser().parse_args(["--mode", "async-distributed", "--wait", "--parallel"])
    assert args.wait and args.parallel
