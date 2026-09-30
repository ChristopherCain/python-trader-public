def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


def safe_div(a, b, default=0.0):
    return a / b if b else default
