import math


def impact_bps(qty: float, available: float, base_bps: float = 0.4) -> float:
    if available <= 0:
        return 100.0
    ratio = max(0, qty / available)
    return base_bps + 8 * math.sqrt(ratio)
