from statistics import fmean


def pearson(a, b):
    n = min(len(a), len(b))
    if n < 2:
        return 0.0
    a = a[-n:]
    b = b[-n:]
    ma = fmean(a)
    mb = fmean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = sum((x - ma) ** 2 for x in a)
    db = sum((y - mb) ** 2 for y in b)
    return num / (da * db) ** 0.5 if da and db else 0.0
