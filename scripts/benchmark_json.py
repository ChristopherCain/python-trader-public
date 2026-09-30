from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
import time
from pathlib import Path

from pythontrader.domain import AssetClass, Instrument, Order, OrderType, Side
from pythontrader.execution.oms import OrderManagementSystem
from pythontrader.marketdata.orderbook import OrderBook
from pythontrader.risk.portfolio_engine import PortfolioRiskEngine


def run(events: int, seed: int) -> dict[str, object]:
    rng = random.Random(seed)
    oms = OrderManagementSystem()
    risk = PortfolioRiskEngine()
    instrument = Instrument("BTC-PERP", AssetClass.PERP, "benchmark", tick_size=0.1, lot_size=0.001)
    latencies_ns: list[int] = []
    accepted = fills = rejects = 0
    digest = hashlib.sha256()

    start = time.perf_counter_ns()
    mark = 50_000.0
    for i in range(events):
        mark *= 1.0 + rng.uniform(-0.0005, 0.0005)
        spread = max(0.1, mark * 0.00005)
        book = OrderBook("BTC-PERP")
        book.reset(
            bids=[(round(mark - spread / 2, 1), 10.0)],
            asks=[(round(mark + spread / 2, 1), 10.0)],
            sequence=i + 1,
            ts=float(i),
        )
        if i % 50:
            continue
        t0 = time.perf_counter_ns()
        side = Side.BUY if rng.random() > 0.5 else Side.SELL
        order = Order(f"bench-{i}", "BTC-PERP", side, 0.01, OrderType.IOC, venue="benchmark")
        decision = risk.check(
            order, instrument, mark, {}, equity=100_000.0, liquidity_usd=1_000_000.0
        )
        if not decision.accepted:
            rejects += 1
            continue
        accepted += 1
        oms.submit(order)
        executions = oms.execute_against_book(order.id, book, ts=float(i))
        fills += len(executions)
        for fill in executions:
            digest.update(f"{fill.order_id}:{fill.qty:.8f}:{fill.price:.8f}".encode())
        latencies_ns.append(time.perf_counter_ns() - t0)
    elapsed_ns = time.perf_counter_ns() - start

    ordered = sorted(latencies_ns)

    def percentile(p: float) -> float:
        if not ordered:
            return 0.0
        idx = min(len(ordered) - 1, int((len(ordered) - 1) * p))
        return ordered[idx] / 1_000_000.0

    return {
        "schema": "pythontrader.benchmark.v1",
        "events": events,
        "seed": seed,
        "accepted_orders": accepted,
        "rejected_orders": rejects,
        "fills": fills,
        "elapsed_ms": elapsed_ns / 1_000_000.0,
        "events_per_second": events / max(elapsed_ns / 1_000_000_000.0, 1e-12),
        "decision_latency_ms": {
            "mean": statistics.fmean(latencies_ns) / 1_000_000.0 if latencies_ns else 0.0,
            "p50": percentile(0.50),
            "p95": percentile(0.95),
            "p99": percentile(0.99),
        },
        "replay_checksum": digest.hexdigest(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(args.events, args.seed)
    text = json.dumps(result, indent=2, sort_keys=True)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
