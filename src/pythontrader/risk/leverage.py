def effective_leverage(gross_exposure, equity):
    return gross_exposure / equity if equity > 0 else float("inf")


def leverage_budget(asset_class, stress):
    base = {"perp": 4.0, "future": 3.0, "fx": 3.0, "crypto": 1.5, "memecoin": 1.0}.get(
        asset_class, 1.0
    )
    return max(1.0, base * (1 - min(0.8, max(0, stress))))
