from __future__ import annotations


def rebalance_orders(
    current: dict[str, float],
    target: dict[str, float],
    marks: dict[str, float],
    threshold: float = 100.0,
) -> dict[str, float]:
    out = {}
    for s, tgt in target.items():
        px = marks.get(s, 0)
        if px <= 0:
            continue
        delta = tgt - current.get(s, 0)
        if abs(delta) >= threshold:
            out[s] = delta / px
    return out
