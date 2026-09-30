from __future__ import annotations


def inverse_vol_weights(vols: dict[str, float], floor: float = 1e-6) -> dict[str, float]:
    inv = {k: 1 / max(floor, v) for k, v in vols.items()}
    total = sum(inv.values())
    return {k: v / total for k, v in inv.items()} if total else {}


def target_notionals(
    equity: float, vols: dict[str, float], gross_fraction: float = 0.8
) -> dict[str, float]:
    w = inverse_vol_weights(vols)
    return {k: equity * gross_fraction * x for k, x in w.items()}
