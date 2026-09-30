from pythontrader.intelligence.brain import TradingBrain


def test_brain_emits_complete_decision():
    d = TradingBrain().infer(
        {"momentum": 0.02, "imbalance": 0.6, "volatility": 0.01, "zscore": 0.5}
    )
    assert d.action in {"buy", "sell", "hold"}
    assert len(d.votes) == 4
    assert 0 < d.confidence <= 1
