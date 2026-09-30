def by_symbol(positions, marks):
    return {s: p.qty * marks.get(s, p.avg_price) for s, p in positions.items()}


def gross(exposures):
    return sum(abs(v) for v in exposures.values())


def net(exposures):
    return sum(exposures.values())
