def meme_score(momentum, liquidity_change, fragility):
    raw = 0.7 * max(-1, min(1, momentum * 15)) + 0.3 * max(-1, min(1, liquidity_change * 5))
    return raw * (1 - max(0, min(1, fragility)))
