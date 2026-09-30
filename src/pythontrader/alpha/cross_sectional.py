def rank_scores(values: dict[str, float]) -> dict[str, float]:
    if not values:
        return {}
    items = sorted(values.items(), key=lambda kv: kv[1])
    n = len(items)
    return {s: (i / (n - 1) * 2 - 1 if n > 1 else 0.0) for i, (s, _) in enumerate(items)}
