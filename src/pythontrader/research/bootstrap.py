import random


def block_bootstrap(xs: list[float], block: int, samples: int, seed: int = 7) -> list[list[float]]:
    if block <= 0:
        raise ValueError("block")
    r = random.Random(seed)
    out = []
    for _ in range(samples):
        row = []
        while len(row) < len(xs):
            i = r.randrange(max(1, len(xs) - block + 1))
            row.extend(xs[i : i + block])
        out.append(row[: len(xs)])
    return out
