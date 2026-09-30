def participation_cap(adv_or_liquidity, asset_class):
    p = {
        "equity": 0.02,
        "etf": 0.03,
        "fx": 0.01,
        "crypto": 0.015,
        "memecoin": 0.0025,
        "perp": 0.01,
        "future": 0.015,
    }.get(asset_class, 0.01)
    return max(0.0, adv_or_liquidity * p)


def impact_bps(order_notional, liquidity):
    if liquidity <= 0:
        return 10_000.0
    return min(10_000.0, 12.0 * (order_notional / liquidity) ** 0.5)
