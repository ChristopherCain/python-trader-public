from pythontrader.domain import Order, OrderType, Side
from pythontrader.execution import (
    ExecutionCoordinator,
    SmartOrderRouter,
    VenueScorer,
    VenueSnapshot,
)
from pythontrader.execution.slippage_model import SlippageModel
from pythontrader.execution.throttle import OrderThrottle


def snapshots():
    return [
        VenueSnapshot("alpha", 99.98, 100.02, 80, 80, 5.0, 1.0, 8.0),
        VenueSnapshot("beta", 99.97, 100.01, 120, 120, 4.0, 1.0, 2.0),
        VenueSnapshot("gamma", 99.95, 100.05, 500, 500, 2.0, 0.5, 85.0, reject_rate=0.04),
    ]


def test_venue_scorer_prefers_lower_effective_cost():
    ranked = VenueScorer().rank(snapshots(), side="buy", qty=50)
    assert ranked[0].venue == "beta"
    assert ranked[0].expected_cost_bps < ranked[-1].expected_cost_bps


def test_router_splits_parent_without_overallocation():
    parent = Order("p1", "XYZ", Side.BUY, 150, OrderType.LIMIT)
    plan = SmartOrderRouter(max_venue_fraction=0.6).route(
        parent, snapshots(), urgency=0.4, adv_notional=5_000_000, volatility_daily=0.02
    )
    assert abs(sum(child.qty for child in plan.children) - plan.routed_qty) < 1e-9
    assert plan.routed_qty <= parent.qty
    assert all(child.qty <= parent.qty * 0.6 + 1e-9 for child in plan.children)


def test_high_urgency_uses_ioc():
    parent = Order("p2", "XYZ", Side.SELL, 40, OrderType.LIMIT)
    plan = SmartOrderRouter().route(
        parent, snapshots(), urgency=0.9, adv_notional=1_000_000, volatility_daily=0.03
    )
    assert plan.children
    assert all(child.order_type is OrderType.IOC for child in plan.children)


def test_slippage_grows_with_size():
    model = SlippageModel()
    small = model.estimate(
        side="buy",
        arrival_price=100,
        spread_bps=2,
        order_notional=10_000,
        adv_notional=10_000_000,
        volatility_daily=0.02,
        participation_rate=0.01,
    )
    large = model.estimate(
        side="buy",
        arrival_price=100,
        spread_bps=2,
        order_notional=500_000,
        adv_notional=10_000_000,
        volatility_daily=0.02,
        participation_rate=0.10,
    )
    assert large.slippage_bps > small.slippage_bps
    assert large.expected_price > small.expected_price


def test_throttle_limits_per_venue():
    throttle = OrderThrottle(global_per_second=10, per_venue_per_second=2)
    assert throttle.check("v", now=1.0).allowed
    assert throttle.check("v", now=1.1).allowed
    third = throttle.check("v", now=1.2)
    assert not third.allowed
    assert third.reason == "venue-rate-limit"
    assert throttle.check("v", now=2.1).allowed


def test_execution_coordinator_runs_end_to_end():
    parent = Order("parent", "XYZ", Side.BUY, 50, OrderType.MARKET, strategy="test")
    report = ExecutionCoordinator().execute_simulated(
        parent, snapshots(), urgency=0.95, adv_notional=2_000_000, volatility_daily=0.015
    )
    assert report.plan.routed_qty > 0
    assert report.filled_qty > 0
    assert report.avg_price > 0
    assert report.fees >= 0
