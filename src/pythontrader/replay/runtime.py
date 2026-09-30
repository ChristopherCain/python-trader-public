from __future__ import annotations

from dataclasses import dataclass
from random import Random
from time import perf_counter

from pythontrader.domain import AssetClass, Instrument, Order, OrderType, Side
from pythontrader.execution.oms import OrderManagementSystem
from pythontrader.intelligence.planner import MarketContext, TradingPlanner
from pythontrader.marketdata.orderbook import OrderBook
from pythontrader.risk.portfolio_engine import PortfolioRiskEngine, PositionView


@dataclass(frozen=True, slots=True)
class ReplayStats:
    events: int
    decisions: int
    orders: int
    fills: int
    rejects: int
    elapsed_s: float
    checksum: int

    @property
    def events_per_second(self) -> float:
        return 0.0 if self.elapsed_s <= 0 else self.events / self.elapsed_s


class DeterministicReplay:
    def __init__(self, *, seed: int = 7) -> None:
        self.rng = Random(seed)
        self.planner = TradingPlanner()
        self.risk = PortfolioRiskEngine()
        self.oms = OrderManagementSystem()
        self.positions: dict[str, PositionView] = {}
        self.cash = 1_000_000.0
        self.checksum = 0

    def run(self, events: int = 100_000) -> ReplayStats:
        instrument = Instrument("BTC-PERP", AssetClass.PERP, "replay", tick_size=0.5)
        book = OrderBook(instrument.symbol)
        mid = 50_000.0
        book.reset(
            [(mid - 0.5 * i, 5 + i) for i in range(1, 21)],
            [(mid + 0.5 * i, 5 + i) for i in range(1, 21)],
            sequence=1,
            ts=0.0,
        )
        decisions = orders = fills = rejects = 0
        start = perf_counter()
        seq = 1
        for i in range(events):
            shock = self.rng.gauss(0.0, 1.8)
            mid = max(100.0, mid + shock)
            seq += 1
            bid = round(mid - 0.5, 1)
            ask = round(mid + 0.5, 1)
            book.reset(
                [(bid - 0.5 * j, 8 + j) for j in range(20)],
                [(ask + 0.5 * j, 8 + j) for j in range(20)],
                sequence=seq,
                ts=float(i),
            )
            self.checksum = ((self.checksum * 1_000_003) ^ int(mid * 100) ^ i) & 0xFFFFFFFFFFFFFFFF
            if i % 37:
                continue
            decisions += 1
            ctx = MarketContext(
                momentum=max(-1.0, min(1.0, shock / 5.0)),
                mean_reversion=max(-1.0, min(1.0, -shock / 7.0)),
                orderflow=book.imbalance(5),
                volatility=min(1.0, abs(shock) / 8.0),
                liquidity=0.9,
                regime_trend=0.35,
                funding=0.0001,
                basis=2.0,
            )
            plan = self.planner.plan(instrument, ctx)
            if plan.action == "hold":
                continue
            side = Side.BUY if plan.action == "buy" else Side.SELL
            qty = max(0.001, plan.size_fraction * 0.025)
            order = Order(
                f"r{i}",
                instrument.symbol,
                side,
                qty,
                OrderType.MARKET,
                strategy="replay",
                venue="replay",
            )
            decision = self.risk.check(
                order, instrument, book.mid or mid, self.positions, equity=self.cash
            )
            if not decision.accepted:
                rejects += 1
                continue
            order.qty = min(order.qty, decision.max_qty)
            self.oms.submit(order)
            orders += 1
            fs = self.oms.execute_against_book(order.id, book, ts=float(i))
            fills += len(fs)
            for fill in fs:
                signed = fill.qty if fill.side is Side.BUY else -fill.qty
                old = self.positions.get(fill.symbol)
                old_qty = 0.0 if old is None else old.qty
                self.positions[fill.symbol] = PositionView(
                    fill.symbol, old_qty + signed, fill.price, asset_class=AssetClass.PERP
                )
                self.cash -= signed * fill.price + fill.fee
        elapsed = perf_counter() - start
        return ReplayStats(events, decisions, orders, fills, rejects, elapsed, self.checksum)
