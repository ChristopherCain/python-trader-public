from __future__ import annotations

import argparse
import json
from statistics import mean
from time import perf_counter

from pythontrader.domain import Order, OrderType, Side
from pythontrader.execution import SmartOrderRouter, VenueSnapshot
from pythontrader.execution.throttle import OrderThrottle


def run(iterations: int) -> dict[str, float | int]:
    router = SmartOrderRouter(
        max_venues=4,
        throttle=OrderThrottle(global_per_second=10_000_000, per_venue_per_second=10_000_000),
    )
    venues = [
        VenueSnapshot("venue-a", 99.98, 100.02, 1000, 1000, 3.0, 1.0, 4.0),
        VenueSnapshot("venue-b", 99.97, 100.01, 800, 800, 4.0, 1.0, 2.0),
        VenueSnapshot("venue-c", 99.96, 100.03, 1500, 1500, 2.0, 0.5, 12.0),
        VenueSnapshot("venue-d", 99.95, 100.04, 2200, 2200, 2.0, 0.5, 40.0, reject_rate=0.01),
    ]
    samples = []
    routed = 0.0
    started = perf_counter()
    for index in range(iterations):
        parent = Order(
            f"bench-{index}",
            "BENCH",
            Side.BUY if index % 2 == 0 else Side.SELL,
            250.0,
            OrderType.LIMIT,
        )
        t0 = perf_counter()
        plan = router.route(
            parent,
            venues,
            urgency=(index % 100) / 100.0,
            adv_notional=25_000_000,
            volatility_daily=0.018,
        )
        samples.append((perf_counter() - t0) * 1_000_000)
        routed += plan.routed_qty
    elapsed = perf_counter() - started
    ordered = sorted(samples)
    p50 = ordered[int(len(ordered) * 0.50)]
    p95 = ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))]
    return {
        "iterations": iterations,
        "elapsed_seconds": round(elapsed, 6),
        "routes_per_second": round(iterations / elapsed, 2),
        "mean_route_us": round(mean(samples), 3),
        "p50_route_us": round(p50, 3),
        "p95_route_us": round(p95, 3),
        "total_routed_qty": round(routed, 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=25_000)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = run(args.iterations)
    print(json.dumps(result, indent=2, sort_keys=True) if args.json else result)


if __name__ == "__main__":
    main()
