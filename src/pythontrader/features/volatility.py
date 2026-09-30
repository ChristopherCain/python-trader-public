import math
from statistics import fmean


def realized_vol(rs: list[float], window: int = 30) -> float:
    x = rs[-window:]
    if len(x) < 2:
        return 0.0
    m = fmean(x)
    return math.sqrt(sum((v - m) ** 2 for v in x) / (len(x) - 1))
