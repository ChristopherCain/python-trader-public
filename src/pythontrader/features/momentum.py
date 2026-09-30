from statistics import fmean


def momentum(xs: list[float], lookback: int = 20) -> float:
    if len(xs) < lookback + 1:
        return 0.0
    return xs[-1] - fmean(xs[-lookback:-1])
