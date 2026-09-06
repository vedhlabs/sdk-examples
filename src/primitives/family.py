import aga_runtime as aga

from primitives.app import app


@app.workflow(name="primitives.family.leaf", version="1")
async def family_leaf(request: dict) -> dict:
    return {
        "order_id": request["order_id"],
        "branch": request["branch"],
        "checked": True,
    }


@app.workflow(name="primitives.family.child", version="1")
async def family_child(request: dict) -> dict:
    inventory = app.start(family_leaf, {**request, "branch": "inventory"})
    shipping = app.start(family_leaf, {**request, "branch": "shipping"})
    branches = await aga.join(inventory, shipping)
    return {"order_id": request["order_id"], "branches": branches}


@app.workflow(name="primitives.family.root", version="1")
async def family_root(request: dict) -> dict:
    aga.event("OrderAccepted", {"order_id": request["order_id"]})
    child = app.start(family_child, request)
    result = await child
    return {"order_id": request["order_id"], "fulfilment": result}
