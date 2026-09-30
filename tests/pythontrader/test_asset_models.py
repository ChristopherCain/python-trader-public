from pythontrader.asset_models.memecoins import MemeCoinContext
from pythontrader.asset_models.options import black_scholes, greeks
from pythontrader.asset_models.perpetuals import PerpState, liquidation_price


def test_perp_math():
    p = PerpState(101, 100, 0.0001, 1_000_000, 5)
    assert 99 < p.basis_bps < 101
    assert liquidation_price(100, "long", 5) < 100


def test_meme_fragility_reduces_capacity():
    safe = MemeCoinContext(10_000_000, 10000, 0.3, 1000, 0.5)
    bad = MemeCoinContext(50_000, 100, 0.9, 2, 2)
    assert safe.fragility() < bad.fragility()
    assert safe.max_notional() > bad.max_notional()


def test_options_analytics():
    p = black_scholes(100, 100, 1, 0.04, 0.2, True)
    g = greeks(100, 100, 1, 0.04, 0.2, True)
    assert 5 < p < 20 and 0 < g["delta"] < 1 and g["gamma"] > 0
