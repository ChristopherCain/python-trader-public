from __future__ import annotations


def fractional_kelly(
    win_rate: float, avg_win: float, avg_loss: float, fraction: float = 0.25, cap: float = 0.1
) -> float:
    if avg_win <= 0 or avg_loss <= 0:
        return 0.0
    b = avg_win / avg_loss
    q = 1 - win_rate
    raw = (b * win_rate - q) / b
    return max(0.0, min(cap, raw * fraction))
