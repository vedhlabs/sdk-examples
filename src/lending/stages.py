from ogha import Quorum

from lending.steps import (
    check_identity,
    decide,
    disburse,
    pull_bureau,
    reserve_funds,
    screen_sanctions,
)


async def run_kyc(ctx, applicant: dict) -> dict:
    identity_h = ctx.call(check_identity, applicant, name="identity")
    sanctions_h = ctx.call(screen_sanctions, applicant, name="sanctions")
    identity, sanctions = await ctx.join(identity_h, sanctions_h)
    if sanctions["sanctioned"]:
        return {"passed": False, "reason": "sanctions_hit"}
    return {"passed": True, "ref": identity["ref"]}


async def run_underwriting(ctx, applicant: dict, amount: int) -> dict:
    pulls = [
        ctx.call(pull_bureau, applicant, bureau, name=f"bureau-{bureau}")
        for bureau in ("experian", "equifax", "transunion")
    ]
    scores = await ctx.join(*pulls, until=Quorum(2))
    for handle in pulls:
        if not handle.settled:
            ctx.cancel(handle, reason="two bureaus already received")
    result = await ctx.call(decide, applicant, scores, amount)
    ctx.emit("Underwritten", result)
    return result


async def run_disbursement(ctx, applicant: dict, amount: int) -> dict:
    reservation = await ctx.call(reserve_funds, applicant, amount)
    transaction = await ctx.call(disburse, applicant, amount)
    return {
        "txn_id": transaction["txn_id"],
        "reservation": reservation["reservation"],
    }

