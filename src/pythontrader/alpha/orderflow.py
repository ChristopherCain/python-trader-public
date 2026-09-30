def orderflow_imbalance(
    bid_size: float, ask_size: float, prev_bid: float = 0, prev_ask: float = 0
) -> float:
    bid_delta = bid_size - prev_bid
    ask_delta = ask_size - prev_ask
    den = abs(bid_delta) + abs(ask_delta)
    return (bid_delta - ask_delta) / den if den else 0.0
