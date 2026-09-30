from pythontrader.market_making.avellaneda import AvellanedaStoikov


def test_quote_is_ordered():
    q = AvellanedaStoikov().quote(100, 0, 0.002)
    assert q.bid < 100 < q.ask and q.size > 0
