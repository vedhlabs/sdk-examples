import asyncio

import pytest

from primitives import loan_journey

LOAN = {"loan_id": "LOAN-42", "applicant": "Demo Applicant"}

WORKFLOW_STEPS = [
    (
        loan_journey.application,
        [
            "loan_capture_application",
            "loan_validate_application",
            "loan_normalize_profile",
            "loan_record_consent",
        ],
    ),
    (
        loan_journey.kyc,
        [
            "loan_verify_tax_identity",
            "loan_verify_address",
            "loan_screen_sanctions",
            "loan_verify_employment",
        ],
    ),
    (
        loan_journey.documents,
        [
            "loan_collect_documents",
            "loan_check_document_completeness",
            "loan_cross_check_documents",
            "loan_archive_documents",
        ],
    ),
    (
        loan_journey.underwriting,
        [
            "loan_pull_bureau_report",
            "loan_calculate_affordability",
            "loan_score_risk",
            "loan_record_underwriting",
        ],
    ),
    (
        loan_journey.approval,
        [
            "loan_assemble_credit_memo",
            "loan_check_policy_limits",
            "loan_create_offer",
            "loan_record_decision",
        ],
    ),
    (
        loan_journey.disbursement,
        [
            "loan_validate_bank_account",
            "loan_prepare_disbursement",
            "loan_release_funds",
            "loan_notify_applicant",
        ],
    ),
]


@pytest.mark.parametrize(("workflow", "step_names"), WORKFLOW_STEPS)
def test_each_loan_workflow_runs_four_distinct_steps(monkeypatch, workflow, step_names):
    calls = []

    def replacement(name):
        async def invoke(_loan):
            calls.append(name)
            return {"stage": name}

        return invoke

    for name in step_names:
        monkeypatch.setattr(loan_journey, name, replacement(name))

    if workflow is loan_journey.underwriting:
        async def child_result():
            return {"workflow": "documents"}

        monkeypatch.setattr(loan_journey.app, "start", lambda *_args: child_result())

    result = asyncio.run(workflow.__wrapped__(LOAN))

    assert calls == step_names
    assert result["loan_id"] == LOAN["loan_id"]
    assert len(result["stages"]) == 4


def test_loan_journey_registers_one_app_with_five_roots_and_one_child():
    expected = set(loan_journey.WORKFLOW_STEP_COUNTS)

    assert expected <= set(loan_journey.app._catalog.workflows)
    assert all(3 <= count <= 5 for count in loan_journey.WORKFLOW_STEP_COUNTS.values())
    assert loan_journey.documents._options.resource is None
