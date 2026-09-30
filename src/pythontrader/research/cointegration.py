from statistics import fmean


def hedge_ratio(x: list[float], y: list[float]) -> float:
    n = min(len(x), len(y))
    if n < 2:
        return 0.0
    x = x[-n:]
    y = y[-n:]
    mx = fmean(x)
    my = fmean(y)
    den = sum((a - mx) ** 2 for a in x)
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / den if den else 0.0


def spread(x: list[float], y: list[float], beta: float) -> list[float]:
    return [b - beta * a for a, b in zip(x, y)]
