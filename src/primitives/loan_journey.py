"""Five independent loan workflows sharing one business ID, plus one real child.

This is a local UI fixture. The steps return illustrative facts only: no credit
bureau, approval service, or payment provider is contacted.
"""

from primitives.app import app


@app.step()
def capture_application(loan: dict) -> dict:
    return {"loan_id": loan["loan_id"], "captured": True}


@app.step()
def verify_identity(loan: dict) -> dict:
    return {"loan_id": loan["loan_id"], "identity": "verified-for-demo"}


@app.step()
def score_loan(loan: dict) -> dict:
    return {"loan_id": loan["loan_id"], "risk_band": "low"}


@app.step()
def inspect_documents(loan: dict) -> dict:
    return {"loan_id": loan["loan_id"], "documents": "checked-for-demo"}


@app.step()
def record_decision(loan: dict) -> dict:
    return {"loan_id": loan["loan_id"], "decision": "approved-for-demo"}


@app.step()
def record_disbursement(loan: dict) -> dict:
    return {"loan_id": loan["loan_id"], "disbursement": "simulated-only"}


@app.workflow(name="loan.demo.documents", version="1")
async def documents(loan: dict) -> dict:
    return await inspect_documents(loan)


@app.workflow(name="loan.demo.application", version="1")
async def application(loan: dict) -> dict:
    return await capture_application(loan)


@app.workflow(name="loan.demo.kyc", version="1")
async def kyc(loan: dict) -> dict:
    return await verify_identity(loan)


@app.workflow(name="loan.demo.underwriting", version="1")
async def underwriting(loan: dict) -> dict:
    score = await score_loan(loan)
    document_result = await app.start(documents, loan)
    return {"score": score, "documents": document_result}


@app.workflow(name="loan.demo.approval", version="1")
async def approval(loan: dict) -> dict:
    return await record_decision(loan)


@app.workflow(name="loan.demo.disbursement", version="1")
async def disbursement(loan: dict) -> dict:
    return await record_disbursement(loan)
