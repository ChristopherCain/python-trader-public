def herfindahl(exposures):
    vals = [abs(v) for v in exposures.values()]
    t = sum(vals)
    return sum((v / t) ** 2 for v in vals) if t else 0.0
