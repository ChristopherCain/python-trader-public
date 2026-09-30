from pythontrader.marketdata.orderbook import OrderBook


def test_orderbook_microprice_and_market_estimate():
    b = OrderBook("X")
    b.reset([(99, 10), (98, 20)], [(101, 30), (102, 50)], sequence=1, ts=1.0)
    assert b.mid == 100
    assert round(b.microprice(), 4) == 99.5
    qty, px = b.estimate_market_order("buy", 40)
    assert qty == 40
    assert 101 < px < 102


def test_sequence_gap_rejected():
    b = OrderBook("X")
    b.reset([(99, 1)], [(101, 1)], sequence=10, ts=1.0)
    try:
        b.update("bid", 98, 1, sequence=12, ts=2.0)
    except ValueError as exc:
        assert "sequence gap" in str(exc)
    else:
        raise AssertionError("expected gap rejection")
