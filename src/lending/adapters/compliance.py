from example_support.store import stable_id


def verify_identity(applicant: dict) -> dict:
    national_id = applicant["national_id"]
    return {"verified": True, "ref": stable_id("kyc", national_id)}


def screen_sanctions(national_id: str) -> dict:
    return {"sanctioned": national_id.upper().startswith("BLOCKED-")}

