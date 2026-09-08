"""Verify five distinct sticky Steps overlap in one KYC Run."""

import os
import uuid

from smoke_first_workflow import worker


def main() -> None:
    namespace = f"kyc-parallel-smoke-{uuid.uuid4().hex[:10]}"
    os.environ["AGA_NAMESPACE"] = namespace
    os.environ.setdefault("AGA_URL", "http://127.0.0.1:8080")
    from quickstart.kyc_parallel import app, kyc_review

    application_id = f"application-{uuid.uuid4().hex[:10]}"
    application = {"application_id": application_id, "applicant": "Smoke Test"}
    try:
        with worker("quickstart.kyc_parallel", os.environ.copy()) as process:
            run = app.start(kyc_review, application)
            result = run.result(timeout=60)
            checks = result["checks"]

            assert result["decision"] == "approved"
            assert len(checks) == 5
            assert {check["check"] for check in checks} == {
                "PAN verification",
                "Employment check",
                "Credit bureau pull",
                "Sanctions screening",
                "Bank account verification",
            }
            assert {check["worker_pid"] for check in checks} == {process.pid}
            assert {check["application_id"] for check in checks} == {application_id}
            assert max(check["started_ns"] for check in checks) < min(
                check["finished_ns"] for check in checks
            )
            print(f"Passed: {run.id}", flush=True)
    finally:
        app.close()
    print(f"Retained scope: default / {namespace}")


if __name__ == "__main__":
    main()
