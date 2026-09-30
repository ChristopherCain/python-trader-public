from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from pythontrader.domain import Order, OrderType
from pythontrader.execution.slippage_model import SlippageModel
from pythontrader.execution.throttle import OrderThrottle
from pythontrader.execution.venue_scoring import VenueScorer, VenueSnapshot


@dataclass(frozen=True, slots=True)
class ChildOrderPlan:
    venue: str
    qty: float
    order_type: OrderType
    limit_price: float | None
    expected_cost_bps: float
    score: float


@dataclass(frozen=True, slots=True)
class RoutingPlan:
    parent_order_id: str
    requested_qty: float
    routed_qty: float
    unallocated_qty: float
    children: tuple[ChildOrderPlan, ...]
    expected_cost_bps: float
    rationale: tuple[str, ...]


class SmartOrderRouter:
    """Multi-venue router using executable depth, fees, latency, slippage and throttling."""

    def __init__(
        self,
        *,
        scorer: VenueScorer | None = None,
        slippage: SlippageModel | None = None,
        throttle: OrderThrottle | None = None,
        max_venues: int = 4,
        max_venue_fraction: float = 0.60,
    ) -> None:
        self.scorer = scorer or VenueScorer()
        self.slippage = slippage or SlippageModel()
        self.throttle = throttle or OrderThrottle()
        self.max_venues = max_venues
        self.max_venue_fraction = max_venue_fraction

    def route(
        self,
        parent: Order,
        snapshots: list[VenueSnapshot],
        *,
        urgency: float,
        adv_notional: float,
        volatility_daily: float,
    ) -> RoutingPlan:
        if not 0 <= urgency <= 1:
            raise ValueError("urgency must be in [0, 1]")
        if not snapshots:
            return RoutingPlan(parent.id, parent.qty, 0.0, parent.qty, (), 0.0, ("no-venues",))

        ranked = self.scorer.rank(snapshots, side=parent.side.value, qty=parent.qty)
        remaining = parent.qty
        children: list[ChildOrderPlan] = []
        weighted_cost = 0.0
        rationale: list[str] = []

        for venue_score in ranked[: self.max_venues]:
            if remaining <= 1e-12 or not isfinite(venue_score.expected_cost_bps):
                continue
            throttle = self.throttle.check(venue_score.venue)
            if not throttle.allowed:
                rationale.append(f"{venue_score.venue}:{throttle.reason}")
                continue

            cap = parent.qty * self.max_venue_fraction
            qty = min(remaining, venue_score.executable_qty, cap)
            if qty <= 0:
                continue

            price = venue_score.effective_price
            notional = qty * price
            slip = self.slippage.estimate(
                side=parent.side.value,
                arrival_price=price,
                spread_bps=max(0.0, venue_score.expected_cost_bps * 0.25),
                order_notional=notional,
                adv_notional=max(adv_notional, notional),
                volatility_daily=volatility_daily,
                participation_rate=min(1.0, qty / max(venue_score.executable_qty, 1e-12)),
            )
            total_cost = venue_score.expected_cost_bps + slip.slippage_bps
            order_type = OrderType.IOC if urgency >= 0.65 else OrderType.LIMIT
            limit_price = None
            if order_type is OrderType.LIMIT:
                edge = max(1.0, venue_score.expected_cost_bps * (0.15 + 0.35 * urgency))
                sign = 1.0 if parent.side.value == "buy" else -1.0
                limit_price = price * (1.0 + sign * edge / 10_000.0)

            children.append(
                ChildOrderPlan(
                    venue=venue_score.venue,
                    qty=qty,
                    order_type=order_type,
                    limit_price=limit_price,
                    expected_cost_bps=total_cost,
                    score=venue_score.score,
                )
            )
            weighted_cost += total_cost * qty
            remaining -= qty

        routed = parent.qty - remaining
        expected = weighted_cost / routed if routed > 0 else 0.0
        if remaining > 1e-12:
            rationale.append("insufficient-executable-depth")
        if len(children) > 1:
            rationale.append("multi-venue-split")
        elif len(children) == 1:
            rationale.append("single-best-venue")
        return RoutingPlan(
            parent.id, parent.qty, routed, remaining, tuple(children), expected, tuple(rationale)
        )
