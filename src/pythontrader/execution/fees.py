def maker_taker_fee(notional, maker=False, maker_bps=-0.05, taker_bps=0.3):
    return notional * (maker_bps if maker else taker_bps) / 10000
