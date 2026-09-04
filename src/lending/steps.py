import ogha

from example_support.store import stable_id, store
from lending.adapters import bureaus, compliance, treasury
from lending.app import app


@app.step(retry=ogha.RetryPolicy(max_attempts=3), timeout=15)
def check_identity(applicant: dict) -> dict:
    if not applicant.get("national_id"):
        raise ValueError("national_id is required")
    return compliance.verify_identity(applicant)


@app.step(retry=ogha.RetryPolicy(max_attempts=2), timeout=15)
def screen_sanctions(applicant: dict) -> dict:
    return compliance.screen_sanctions(applicant["national_id"])


@app.step(retry=ogha.RetryPolicy(max_attempts=4), timeout=30)
def pull_bureau(applicant: dict, bureau: str) -> dict:
    return {"bureau": bureau, "score": bureaus.credit_score(bureau, applicant)}


@app.step(timeout=15)
def decide(applicant: dict, scores: list[dict], amount: int) -> dict:
    average = sum(score["score"] for score in scores) / len(scores)
    limit = 300_000 if average >= 720 else 150_000 if average >= 660 else 0
    if average < 600:
        return {"avg": round(average), "decision": "decline"}
    return {
        "avg": round(average),
        "auto_limit": limit,
        "decision": "auto_approve" if amount <= limit else "needs_review",
        "applicant_id": applicant["id"],
    }


@app.step(
    retry=ogha.RetryPolicy(max_attempts=3),
    timeout=30,
    compensate_with="release_reserve",
)
def reserve_funds(applicant: dict, amount: int) -> dict:
    return treasury.reserve(
        applicant_id=applicant["id"],
        amount=amount,
        idempotency_key=f"loan:{applicant['id']}:reserve",
    )


@app.step()
def release_reserve(reservation: dict) -> dict:
    return treasury.release(reservation["reservation"])


@app.step(retry=ogha.RetryPolicy(max_attempts=5), pivot=True, timeout=45)
def disburse(applicant: dict, amount: int) -> dict:
    return treasury.disburse(
        applicant_id=applicant["id"],
        amount=amount,
        idempotency_key=f"loan:{applicant['id']}:disburse",
    )


@app.step(retry=ogha.RetryPolicy(max_attempts=3), timeout=30)
def build_statement(borrower: dict, period: str) -> dict:
    key = f"{borrower['id']}:{period}"
    return store.once(
        "lending.statements.build",
        key,
        lambda: {
            "statement_id": stable_id("stmt", key),
            "borrower_id": borrower["id"],
            "period": period,
        },
    )
