from primitives.app import app


@app.step()
def family_stage(request: dict, stage: str) -> dict:
    return {"order_id": request["order_id"], "stage": stage, "completed": True}


async def run_stages(request: dict, names: tuple[str, ...]) -> list[dict]:
    completed = []
    for name in names:
        completed.append(await family_stage.options(name=name)(request, name))
    return completed


@app.workflow(name="primitives.family.finalize", version="1")
async def family_finalize(request: dict) -> dict:
    stages = await run_stages(request, ("reserve", "label", "confirm"))
    return {"order_id": request["order_id"], "stages": stages}


@app.workflow(name="primitives.family.fulfilment", version="1")
async def family_fulfilment(request: dict) -> dict:
    stages = await run_stages(
        request,
        ("check-inventory", "quote-carrier", "plan-pack", "authorize"),
    )
    final = await app.start(family_finalize, request)
    return {"order_id": request["order_id"], "stages": stages, "final": final}


@app.workflow(name="primitives.family.loop", version="1")
async def family_loop(request: dict) -> dict:
    stages = await run_stages(request, ("loop-1", "loop-2", "loop-3"))
    fulfilment = await app.start(family_fulfilment, request)
    return {"order_id": request["order_id"], "stages": stages, "fulfilment": fulfilment}


@app.workflow(name="primitives.family.root", version="1")
async def family_root(request: dict) -> dict:
    stages = await run_stages(
        request,
        ("accept-order", "validate-order", "reserve-request", "route-request"),
    )
    child = await app.start(family_loop, request)
    return {"order_id": request["order_id"], "stages": stages, "child": child}
