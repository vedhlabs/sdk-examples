import time

import aga_runtime as aga

from primitives.app import app


@app.step()
def normalize_request(request: dict) -> dict:
    return {"customer": request["customer"].strip().lower(), "amount": int(request["amount"])}


@app.step(name="risk.score", retry=aga.RetryPolicy(max_attempts=3), timeout=10)
def risk_score(request: dict) -> dict:
    score = 25 if request["amount"] < 1_000 else 70
    return {"score": score, "band": "low" if score < 50 else "high"}


@app.step()
def quote_provider(request: dict, provider: str) -> dict:
    latency = {"fast": 0.04, "slow": 0.25}[provider]
    time.sleep(latency)
    return {"provider": provider, "price": request["amount"] + (5 if provider == "fast" else 3)}


@app.step()
def create_child_record(request: dict) -> dict:
    return {"child_record": f"record:{request['customer']}"}


@app.remote("primitives", name="risk.score", timeout=10)
def remote_risk_score(request: dict) -> dict:
    raise NotImplementedError("remote declarations are routed, not called locally")


@app.workflow(name="primitives.child")
async def child_workflow(request: dict) -> dict:
    return await create_child_record(request)


@app.workflow(
    name="primitives.tour",
    version="1",
    execution="async_distributed",
)
async def methods_tour(request: dict) -> dict:
    normalized = await normalize_request(request)
    risk = await remote_risk_score(normalized)

    child = app.start(child_workflow, normalized)
    quotes = {
        provider: quote_provider.options(name=f"quote-{provider}")(
            normalized, provider
        )
        for provider in ("fast", "slow")
    }
    first_quote = (await aga.join(*quotes.values(), count=1))[0]
    for provider, handle in quotes.items():
        if provider != first_quote["provider"]:
            aga.cancel(handle, reason="first quote already selected")
    child_result = await child

    await aga.sleep(1)
    signal = await aga.signal("external_signal", timeout=60)
    approval = await aga.signal(
        aga.Approval(
            "manual_approval",
            {"risk": risk, "quote": first_quote},
        ),
        timeout=60,
    )
    aga.event("TourCompleted", {"approved_by": approval["reviewer"]})
    return {
        "normalized": normalized,
        "risk": risk,
        "quote": first_quote,
        "child": child_result,
        "signal": signal,
        "approval": approval,
    }
