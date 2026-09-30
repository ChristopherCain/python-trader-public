UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_timeframe(v):
    n = int(v[:-1])
    u = v[-1].lower()
    if u not in UNITS:
        raise ValueError(v)
    return n * UNITS[u]
