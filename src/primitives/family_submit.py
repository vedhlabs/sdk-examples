import argparse
import hashlib
import uuid

import aga_runtime as aga

from primitives.app import app
from primitives.family import family_root


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit a traceable execution family")
    parser.add_argument("--order-id", default=f"ORDER-{uuid.uuid4().hex[:12]}")
    parser.add_argument("--wait", action="store_true")
    args = parser.parse_args()

    configured = family_root.options(
        run_id=f"family-{hashlib.sha256(args.order_id.encode()).hexdigest()[:32]}",
        resource=aga.ResourceRef("order", args.order_id),
    )
    run = app.start(configured, {"order_id": args.order_id})
    print(run.result() if args.wait else run.id)


if __name__ == "__main__":
    main()
