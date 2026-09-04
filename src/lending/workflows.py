import ogha

from lending.app import app
from lending.stages import run_disbursement, run_kyc, run_underwriting
from lending.steps import build_statement


@app.workflow(
    name="lending.kyc",
    version="1",
    execution="async_distributed",
)
async def kyc(applicant: dict) -> dict:
    return await run_kyc(applicant)


@app.workflow(
    name="lending.underwriting",
    version="1",
    execution="async_distributed",
)
async def underwriting(request: dict) -> dict:
    return await run_underwriting(request["applicant"], int(request["amount"]))


@app.workflow(
    name="lending.disbursement",
    version="1",
    execution="async_distributed",
)
async def disbursement(request: dict) -> dict:
    return await run_disbursement(request["applicant"], int(request["amount"]))


@app.workflow(
    name="lending.application",
    version="1",
    execution="async_distributed",
)
async def application(request: dict) -> dict:
    applicant = request["applicant"]
    amount = int(request["amount"])
    ogha.event("ApplicationReceived", {"id": applicant["id"], "amount": amount})

    kyc_result = await run_kyc(applicant)
    if not kyc_result["passed"]:
        return {"status": "rejected", "stage": "kyc", "reason": kyc_result["reason"]}

    underwriting_result = await run_underwriting(applicant, amount)
    if underwriting_result["decision"] == "decline":
        return {
            "status": "rejected",
            "stage": "underwriting",
            "avg_score": underwriting_result["avg"],
        }

    if underwriting_result["decision"] == "needs_review":
        try:
            approval = await ogha.signal(
                ogha.Approval(
                    "manual_underwriting",
                    {"applicant": applicant["id"], "amount": amount},
                ),
                timeout=120,
            )
        except ogha.PermissionDenied:
            return {"status": "rejected", "stage": "approval", "reason": "not answered"}
        if not approval.get("approved"):
            return {"status": "rejected", "stage": "approval", "reason": "denied"}

    disbursement_result = await run_disbursement(applicant, amount)
    ogha.event("Disbursed", {"txn": disbursement_result["txn_id"], "amount": amount})
    return {
        "status": "disbursed",
        "applicant": applicant["id"],
        "txn_id": disbursement_result["txn_id"],
        "avg_score": underwriting_result["avg"],
    }


@app.workflow(name="lending.statement", version="1")
async def statement(request: dict) -> dict:
    return await build_statement(request["borrower"], request["period"])


@app.workflow(name="lending.month_end", version="1")
async def month_end(request: dict) -> dict:
    borrowers = request["borrowers"]
    period = request["period"]
    children = [
        statement.options(
            run_id=f"{period}-{borrower['id']}",
            detached=True,
        ).spawn(
            {"borrower": borrower, "period": period},
        )
        for borrower in borrowers
    ]
    ogha.event("MonthEndStarted", {"count": len(children), "period": period})
    return {"started": len(children), "run_ids": [child.id for child in children]}
