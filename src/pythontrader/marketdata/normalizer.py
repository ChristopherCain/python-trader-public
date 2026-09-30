from pythontrader.domain import Quote


def normalize_quote(symbol, bid, ask, bid_size=0, ask_size=0):
    b = float(bid)
    a = float(ask)
    if b <= 0 or a <= 0 or b > a:
        raise ValueError("bad quote")
    return Quote(symbol.upper(), b, a, max(0, float(bid_size)), max(0, float(ask_size)))
