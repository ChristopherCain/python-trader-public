def pair_signal(zscore, entry=2.0, exit=0.4):
    if zscore > entry:
        return -1.0
    if zscore < -entry:
        return 1.0
    if abs(zscore) < exit:
        return 0.0
    return max(-1.0, min(1.0, -zscore / entry))
