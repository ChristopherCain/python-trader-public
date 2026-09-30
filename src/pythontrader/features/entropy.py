import math


def directional_entropy(rs: list[float], window: int = 50) -> float:
    x = rs[-window:]
    if not x:
        return 0.0
    p = sum(1 for r in x if r > 0) / len(x)
    if p in (0, 1):
        return 0.0
    return -(p * math.log(p) + (1 - p) * math.log(1 - p))
