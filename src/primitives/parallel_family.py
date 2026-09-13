"""A parent Run with three owned child Workflows executing in parallel."""

from __future__ import annotations

import random
import time
from collections.abc import Mapping

from primitives.app import app


def perform_check(
    application: Mapping[str, object],
    check: str,
    outcome: Mapping[str, object],
) -> dict[str, object]:
    """Spend enough time in a Step for overlap to be obvious in the UI."""
    delay_seconds = random.uniform(2, 3)
    time.sleep(delay_seconds)
    return {
        "application_id": application["application_id"],
        "check": check,
        "delay_seconds": round(delay_seconds, 3),
        **outcome,
    }


@app.step()
def verify_pan(application: dict[str, object]) -> dict[str, object]:
    return perform_check(application, "PAN verification", {"status": "verified"})


@app.step()
def screen_sanctions(application: dict[str, object]) -> dict[str, object]:
    return perform_check(application, "Sanctions screening", {"matches": 0})


@app.step()
def verify_employment(application: dict[str, object]) -> dict[str, object]:
    return perform_check(application, "Employment verification", {"status": "active"})


@app.step()
def verify_income(application: dict[str, object]) -> dict[str, object]:
    return perform_check(application, "Income verification", {"status": "verified"})


@app.step()
def pull_bureau(application: dict[str, object]) -> dict[str, object]:
    return perform_check(application, "Credit bureau pull", {"score": 762})


@app.step()
def detect_fraud(application: dict[str, object]) -> dict[str, object]:
    return perform_check(application, "Fraud screening", {"risk": "low"})


@app.workflow(name="primitives.parallel-family.identity", version="1")
async def identity_checks(application: dict[str, object]) -> dict[str, object]:
    results = await app.join(verify_pan(application), screen_sanctions(application))
    return {"group": "identity", "checks": results}


@app.workflow(name="primitives.parallel-family.employment", version="1")
async def employment_checks(application: dict[str, object]) -> dict[str, object]:
    results = await app.join(
        verify_employment(application),
        verify_income(application),
    )
    return {"group": "employment", "checks": results}


@app.workflow(name="primitives.parallel-family.financial", version="1")
async def financial_checks(application: dict[str, object]) -> dict[str, object]:
    results = await app.join(pull_bureau(application), detect_fraud(application))
    return {"group": "financial", "checks": results}


@app.workflow(name="primitives.parallel-family.root", version="1")
async def parallel_family_root(application: dict[str, object]) -> dict[str, object]:
    """Start all children before waiting, so their work can overlap."""
    identity = app.start(identity_checks, application)
    employment = app.start(employment_checks, application)
    financial = app.start(financial_checks, application)

    results = await app.join(identity, employment, financial)
    return {
        "application_id": application["application_id"],
        "decision": "approved",
        "children": results,
    }

