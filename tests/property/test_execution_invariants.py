import random

from pythontrader.domain import Order, OrderType, Side
from pythontrader.execution.smart_order_router import SmartOrderRouter
from pythontrader.execution.venue_scoring import VenueSnapshot


def test_router_quantity_conservation_over_generated_inputs():
    rng = random.Random(20261001)
    router = SmartOrderRouter(max_venue_fraction=0.55)
    for index in range(250):
        qty = rng.uniform(0.01, 10_000)
        side = Side.BUY if rng.random() < 0.5 else Side.SELL
        order = Order(f"p{index}", "XYZ", side, qty, OrderType.LIMIT)
        snapshots = []
        for venue_index in range(rng.randint(1, 5)):
            mid = rng.uniform(5, 5_000)
            spread = rng.uniform(0.0001, 0.005) * mid
            snapshots.append(
                VenueSnapshot(
                    f"v{venue_index}",
                    mid - spread / 2,
                    mid + spread / 2,
                    rng.uniform(0.1, qty * 2),
                    rng.uniform(0.1, qty * 2),
                    rng.uniform(0, 15),
                    rng.uniform(0, 5),
                    rng.uniform(0.1, 150),
                    reject_rate=rng.uniform(0, 0.08),
                    stale_ms=rng.uniform(0, 500),
                )
            )
        plan = router.route(
            order,
            snapshots,
            urgency=rng.random(),
            adv_notional=rng.uniform(100_000, 100_000_000),
            volatility_daily=rng.uniform(0, 0.15),
        )
        assert plan.routed_qty >= 0
        assert plan.unallocated_qty >= -1e-9
        assert abs(plan.routed_qty + plan.unallocated_qty - qty) < 1e-6
        assert abs(sum(child.qty for child in plan.children) - plan.routed_qty) < 1e-6
        assert all(child.qty > 0 for child in plan.children)
