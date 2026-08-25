import ogha

from lending.stages import run_disbursement, run_kyc, run_underwriting
from lending.steps import build_statement


@ogha.workflow(
    name="lending.kyc",
    version="1",
    execution="async_distributed",
    target="python://lending",
)
async def kyc(ctx, applicant: dict) -> dict:
    return await run_kyc(ctx, applicant)


@ogha.workflow(
    name="lending.underwriting",
    version="1",
    execution="async_distributed",
    target="python://lending",
)
async def underwriting(ctx, request: dict) -> dict:
    return await run_underwriting(ctx, request["applicant"], int(request["amount"]))


@ogha.workflow(
    name="lending.disbursement",
    version="1",
    execution="async_distributed",
    target="python://lending",
)
async def disbursement(ctx, request: dict) -> dict:
    return await run_disbursement(ctx, request["applicant"], int(request["amount"]))


@ogha.workflow(
    name="lending.application",
    version="1",
    execution="async_distributed",
    target="python://lending",
)
async def application(ctx, request: dict) -> dict:
    applicant = request["applicant"]
    amount = int(request["amount"])
    ctx.emit("ApplicationReceived", {"id": applicant["id"], "amount": amount})

    kyc_result = await run_kyc(ctx, applicant)
    if not kyc_result["passed"]:
        return {"status": "rejected", "stage": "kyc", "reason": kyc_result["reason"]}

    underwriting_result = await run_underwriting(ctx, applicant, amount)
    if underwriting_result["decision"] == "decline":
        return {
            "status": "rejected",
            "stage": "underwriting",
            "avg_score": underwriting_result["avg"],
        }

    if underwriting_result["decision"] == "needs_review":
        try:
            approval = await ctx.gate(
                "manual_underwriting",
                {"applicant": applicant["id"], "amount": amount},
                timeout=120,
            )
        except ogha.PermissionDenied:
            return {"status": "rejected", "stage": "approval", "reason": "not answered"}
        if not approval.get("approved"):
            return {"status": "rejected", "stage": "approval", "reason": "denied"}

    disbursement_result = await run_disbursement(ctx, applicant, amount)
    ctx.emit("Disbursed", {"txn": disbursement_result["txn_id"], "amount": amount})
    return {
        "status": "disbursed",
        "applicant": applicant["id"],
        "txn_id": disbursement_result["txn_id"],
        "avg_score": underwriting_result["avg"],
    }


@ogha.workflow(name="lending.statement", version="1", target="python://lending")
async def statement(ctx, request: dict) -> dict:
    return await ctx.call(build_statement, request["borrower"], request["period"])


@ogha.workflow(name="lending.month_end", version="1", target="python://lending")
async def month_end(ctx, request: dict) -> dict:
    borrowers = request["borrowers"]
    period = request["period"]
    children = [
        ctx.spawn(
            "lending.statement",
            {"borrower": borrower, "period": period},
            target="python://lending",
        )
        for borrower in borrowers
    ]
    ctx.emit("MonthEndStarted", {"count": len(children), "period": period})
    return {"started": len(children), "run_ids": [child.id for child in children]}
