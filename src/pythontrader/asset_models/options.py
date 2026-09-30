from math import erf, exp, log, pi, sqrt


def _n(x):
    return exp(-x * x / 2) / sqrt(2 * pi)


def _N(x):
    return 0.5 * (1 + erf(x / sqrt(2)))


def black_scholes(spot, strike, t, rate, vol, call=True):
    if min(spot, strike, t, vol) <= 0:
        return max(0.0, (spot - strike) if call else (strike - spot))
    d1 = (log(spot / strike) + (rate + 0.5 * vol * vol) * t) / (vol * sqrt(t))
    d2 = d1 - vol * sqrt(t)
    return (
        spot * _N(d1) - strike * exp(-rate * t) * _N(d2)
        if call
        else strike * exp(-rate * t) * _N(-d2) - spot * _N(-d1)
    )


def greeks(spot, strike, t, rate, vol, call=True):
    d1 = (log(spot / strike) + (rate + 0.5 * vol * vol) * t) / (vol * sqrt(t))
    delta = _N(d1) if call else _N(d1) - 1
    gamma = _n(d1) / (spot * vol * sqrt(t))
    vega = spot * _n(d1) * sqrt(t) / 100
    return {"delta": delta, "gamma": gamma, "vega": vega}
