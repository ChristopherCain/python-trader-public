def pip_size(symbol: str) -> float:
    return 0.01 if symbol.endswith("JPY") else 0.0001


def pips(symbol: str, a: float, b: float) -> float:
    return (b - a) / pip_size(symbol)
