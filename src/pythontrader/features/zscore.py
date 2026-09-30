import math
from statistics import fmean


def zscore(xs: list[float], window: int = 50) -> float:
    x = xs[-window:]
    if len(x) < 3:
        return 0.0
    m = fmean(x)
    sd = math.sqrt(sum((v - m) ** 2 for v in x) / (len(x) - 1))
    return (x[-1] - m) / sd if sd else 0.0
