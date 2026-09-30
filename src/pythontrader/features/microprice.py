def microprice(bid: float, ask: float, bid_size: float, ask_size: float) -> float:
    t = bid_size + ask_size
    if t <= 0:
        return (bid + ask) / 2
    return (ask * bid_size + bid * ask_size) / t
