from statistics import fmean


def rolling_mean(xs: list[float], window: int) -> list[float]:
    if window <= 0:
        raise ValueError("window")
    return [fmean(xs[max(0, i - window + 1) : i + 1]) for i in range(len(xs))]


def ema(xs: list[float], alpha: float) -> list[float]:
    if not xs:
        return []
    if not 0 < alpha <= 1:
        raise ValueError("alpha")
    out = [xs[0]]
    for x in xs[1:]:
        out.append(alpha * x + (1 - alpha) * out[-1])
    return out
