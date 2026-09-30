from statistics import fmean


def average_slippage_bps(expected, actual):
    vals = [abs(a / e - 1) * 10000 for e, a in zip(expected, actual) if e]
    return fmean(vals) if vals else 0.0
