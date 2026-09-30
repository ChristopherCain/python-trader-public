from statistics import fmean


def trend_score(prices: list[float], fast: int = 8, slow: int = 32) -> float:
    if len(prices) < slow:
        return 0.0
    a = fmean(prices[-fast:])
    b = fmean(prices[-slow:])
    return max(-1, min(1, (a / b - 1) * 50)) if b else 0.0
