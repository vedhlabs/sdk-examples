import aga_runtime as aga

from lending.steps import (
    check_identity,
    decide,
    disburse,
    pull_bureau,
    reserve_funds,
    screen_sanctions,
)


async def run_kyc(applicant: dict) -> dict:
    identity_h = check_identity.options(name="identity")(applicant)
    sanctions_h = screen_sanctions.options(name="sanctions")(applicant)
    identity, sanctions = await aga.join(identity_h, sanctions_h)
    if sanctions["sanctioned"]:
        return {"passed": False, "reason": "sanctions_hit"}
    return {"passed": True, "ref": identity["ref"]}


async def run_underwriting(applicant: dict, amount: int) -> dict:
    pulls = {
        bureau: pull_bureau.options(name=f"bureau-{bureau}")(applicant, bureau)
        for bureau in ("experian", "equifax", "transunion")
    }
    scores = await aga.join(*pulls.values(), count=2)
    winning_bureaus = {score["bureau"] for score in scores}
    for bureau, handle in pulls.items():
        if bureau not in winning_bureaus:
            aga.cancel(handle, reason="two bureaus already received")
    result = await decide(applicant, scores, amount)
    aga.event("Underwritten", result)
    return result


async def run_disbursement(applicant: dict, amount: int) -> dict:
    reservation = await reserve_funds(applicant, amount)
    transaction = await disburse(applicant, amount)
    return {
        "txn_id": transaction["txn_id"],
        "reservation": reservation["reservation"],
    }
