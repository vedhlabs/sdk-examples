import time

_PROFILE = {
    "experian": {"offset": 0, "latency": 0.04},
    "equifax": {"offset": -6, "latency": 0.07},
    "transunion": {"offset": 4, "latency": 0.25},
}


def credit_score(bureau: str, applicant: dict) -> int:
    if bureau not in _PROFILE:
        raise ValueError(f"unsupported bureau: {bureau}")
    profile = _PROFILE[bureau]
    time.sleep(profile["latency"])
    requested = int(applicant.get("requested_score", 720))
    return max(300, min(850, requested + profile["offset"]))

