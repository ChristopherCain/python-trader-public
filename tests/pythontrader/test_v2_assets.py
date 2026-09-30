from pythontrader.asset_models.memecoin_engine import MemecoinModel, MemeMarketState
from pythontrader.asset_models.perps_engine import PerpetualModel, PerpMarketState, PerpPosition


def test_perp_liquidation_distance_and_funding():
    m = PerpetualModel()
    p = PerpPosition(qty=1, entry=50_000, leverage=5, collateral=10_000)
    s = PerpMarketState(
        mark=50_500, index=50_450, funding_rate=0.0001, open_interest_usd=10_000_000
    )
    assert m.funding_payment(p, s) < 0
    assert m.liquidation_distance_bps(p, s) > 0


def test_memecoin_risk_flags_thin_pool():
    s = MemeMarketState(1, 1_000_000, 5_000, 30_000, 0.8, 0.12, 4.0, 20, 0.5)
    score = MemecoinModel().score(s)
    assert "thin_liquidity" in score.notes
    assert score.score < 0.6
