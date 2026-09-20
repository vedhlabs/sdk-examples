"""One loan application observed across five workflows and one real child.

Every workflow performs four illustrative durable Steps. The functions sleep
briefly so their measured work is visible in the local waterfall; they do not
contact a bureau, identity provider, approval service, or payment rail.
"""

from __future__ import annotations

import time
from collections.abc import Mapping

from primitives.app import app


def complete_demo_step(
    loan: Mapping[str, object],
    stage: str,
    **facts: object,
) -> dict[str, object]:
    """Return a small, visible, deterministic unit of simulated work."""
    time.sleep(0.12)
    return {"loan_id": loan["loan_id"], "stage": stage, **facts}


# Application intake


@app.step(name="loan.capture-application")
def loan_capture_application(loan: dict[str, object]) -> dict[str, object]:
    return complete_demo_step(loan, "capture-application", captured=True)


@app.step(name="loan.validate-application")
def loan_validate_application(loan: dict[str, object]) -> dict[str, object]:
    return complete_demo_step(loan, "validate-application", valid=True)


@app.step(name="loan.normalize-profile")
def loan_normalize_profile(loan: dict[str, object]) -> dict[str, object]:
    return complete_demo_step(loan, "normalize-profile", profile="normalized")


@app.step(name="loan.record-consent")
def loan_record_consent(loan: dict[str, object]) -> dict[str, object]:
    return complete_demo_step(loan, "record-consent", consent="recorded")


# KYC


@app.step(name="loan.verify-tax-identity")
def loan_verify_tax_identity(loan: dict[str, object]) -> dict[str, object]:
    return complete_demo_step(loan, "verify-tax-identity", identity="verified")


@app.step(name="loan.verify-address")
def loan_verify_address(loan: dict[str, object]) -> dict[str, object]:
    return complete_demo_step(loan, "verify-address", address="verified")


@app.step(name="loan.screen-sanctions")
def loan_screen_sanctions(loan: dict[str, object]) -> dict[str, object]:
    return complete_demo_step(loan, "screen-sanctions", matches=0)


@app.step(name="loan.verify-employment")
def loan_verify_employment(loan: dict[str, object]) -> dict[str, object]:
    return complete_demo_step(loan, "verify-employment", employment="active")


# Document child


@app.step(name="loan.collect-documents")
def loan_collect_documents(loan: dict[str, object]) -> dict[str, object]:
    return complete_demo_step(loan, "collect-documents", received=4)


@app.step(name="loan.check-document-completeness")
def loan_check_document_completeness(loan: dict[str, object]) -> dict[str, object]:
    return complete_demo_step(loan, "check-document-completeness", complete=True)


@app.step(name="loan.cross-check-documents")
def loan_cross_check_documents(loan: dict[str, object]) -> dict[str, object]:
    return complete_demo_step(loan, "cross-check-documents", mismatches=0)


@app.step(name="loan.archive-documents")
def loan_archive_documents(loan: dict[str, object]) -> dict[str, object]:
    return complete_demo_step(loan, "archive-documents", archived=True)


# Underwriting


@app.step(name="loan.pull-bureau-report")
def loan_pull_bureau_report(loan: dict[str, object]) -> dict[str, object]:
    return complete_demo_step(loan, "pull-bureau-report", score=762)


@app.step(name="loan.calculate-affordability")
def loan_calculate_affordability(loan: dict[str, object]) -> dict[str, object]:
    return complete_demo_step(loan, "calculate-affordability", ratio=0.31)


@app.step(name="loan.score-risk")
def loan_score_risk(loan: dict[str, object]) -> dict[str, object]:
    return complete_demo_step(loan, "score-risk", risk_band="low")


@app.step(name="loan.record-underwriting")
def loan_record_underwriting(loan: dict[str, object]) -> dict[str, object]:
    return complete_demo_step(loan, "record-underwriting", eligible=True)


# Approval


@app.step(name="loan.assemble-credit-memo")
def loan_assemble_credit_memo(loan: dict[str, object]) -> dict[str, object]:
    return complete_demo_step(loan, "assemble-credit-memo", memo="ready")


@app.step(name="loan.check-policy-limits")
def loan_check_policy_limits(loan: dict[str, object]) -> dict[str, object]:
    return complete_demo_step(loan, "check-policy-limits", within_limits=True)


@app.step(name="loan.create-offer")
def loan_create_offer(loan: dict[str, object]) -> dict[str, object]:
    return complete_demo_step(loan, "create-offer", offer="standard")


@app.step(name="loan.record-decision")
def loan_record_decision(loan: dict[str, object]) -> dict[str, object]:
    return complete_demo_step(loan, "record-decision", decision="approved-for-demo")


# Disbursement


@app.step(name="loan.validate-bank-account")
def loan_validate_bank_account(loan: dict[str, object]) -> dict[str, object]:
    return complete_demo_step(loan, "validate-bank-account", account="verified")


@app.step(name="loan.prepare-disbursement")
def loan_prepare_disbursement(loan: dict[str, object]) -> dict[str, object]:
    return complete_demo_step(loan, "prepare-disbursement", instruction="prepared")


@app.step(name="loan.release-funds")
def loan_release_funds(loan: dict[str, object]) -> dict[str, object]:
    return complete_demo_step(loan, "release-funds", release="simulated-only")


@app.step(name="loan.notify-applicant")
def loan_notify_applicant(loan: dict[str, object]) -> dict[str, object]:
    return complete_demo_step(loan, "notify-applicant", notification="queued")


@app.workflow(name="loan.demo.documents", version="1")
async def documents(loan: dict[str, object]) -> dict[str, object]:
    stages = [
        await loan_collect_documents(loan),
        await loan_check_document_completeness(loan),
        await loan_cross_check_documents(loan),
        await loan_archive_documents(loan),
    ]
    return {"loan_id": loan["loan_id"], "workflow": "documents", "stages": stages}


@app.workflow(name="loan.demo.application", version="1")
async def application(loan: dict[str, object]) -> dict[str, object]:
    stages = [
        await loan_capture_application(loan),
        await loan_validate_application(loan),
        await loan_normalize_profile(loan),
        await loan_record_consent(loan),
    ]
    return {"loan_id": loan["loan_id"], "workflow": "application", "stages": stages}


@app.workflow(name="loan.demo.kyc", version="1")
async def kyc(loan: dict[str, object]) -> dict[str, object]:
    stages = [
        await loan_verify_tax_identity(loan),
        await loan_verify_address(loan),
        await loan_screen_sanctions(loan),
        await loan_verify_employment(loan),
    ]
    return {"loan_id": loan["loan_id"], "workflow": "kyc", "stages": stages}


@app.workflow(name="loan.demo.underwriting", version="1")
async def underwriting(loan: dict[str, object]) -> dict[str, object]:
    document_run = app.start(documents, loan)
    stages = [
        await loan_pull_bureau_report(loan),
        await loan_calculate_affordability(loan),
        await loan_score_risk(loan),
        await loan_record_underwriting(loan),
    ]
    return {
        "loan_id": loan["loan_id"],
        "workflow": "underwriting",
        "stages": stages,
        "documents": await document_run,
    }


@app.workflow(name="loan.demo.approval", version="1")
async def approval(loan: dict[str, object]) -> dict[str, object]:
    stages = [
        await loan_assemble_credit_memo(loan),
        await loan_check_policy_limits(loan),
        await loan_create_offer(loan),
        await loan_record_decision(loan),
    ]
    return {"loan_id": loan["loan_id"], "workflow": "approval", "stages": stages}


@app.workflow(name="loan.demo.disbursement", version="1")
async def disbursement(loan: dict[str, object]) -> dict[str, object]:
    stages = [
        await loan_validate_bank_account(loan),
        await loan_prepare_disbursement(loan),
        await loan_release_funds(loan),
        await loan_notify_applicant(loan),
    ]
    return {"loan_id": loan["loan_id"], "workflow": "disbursement", "stages": stages}


WORKFLOW_STEP_COUNTS = {
    "loan.demo.application": 4,
    "loan.demo.kyc": 4,
    "loan.demo.underwriting": 4,
    "loan.demo.documents": 4,
    "loan.demo.approval": 4,
    "loan.demo.disbursement": 4,
}
