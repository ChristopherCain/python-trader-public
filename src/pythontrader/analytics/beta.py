from statistics import fmean


def beta(asset, benchmark):
    n = min(len(asset), len(benchmark))
    if n < 2:
        return 0.0
    a = asset[-n:]
    b = benchmark[-n:]
    ma = fmean(a)
    mb = fmean(b)
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (n - 1)
    var = sum((x - mb) ** 2 for x in b) / (n - 1)
    return cov / var if var else 0.0
