import time

_QUOTES = {"ups": (18, 0.04), "fedex": (16, 0.07), "dhl": (14, 0.25)}


def quote(order: dict, carrier: str) -> int:
    if carrier not in _QUOTES:
        raise ValueError(f"unsupported carrier: {carrier}")
    price, latency = _QUOTES[carrier]
    time.sleep(latency)
    item_count = sum(int(item["qty"]) for item in order["items"])
    return price + max(0, item_count - 1) * 2

