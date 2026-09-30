from __future__ import annotations

from dataclasses import dataclass
from math import inf


@dataclass(frozen=True, slots=True)
class VenueSnapshot:
    venue: str
    bid: float
    ask: float
    bid_size: float
    ask_size: float
    taker_fee_bps: float
    maker_fee_bps: float
    latency_ms: float
    reject_rate: float = 0.0
    stale_ms: float = 0.0

    @property
    def spread_bps(self) -> float:
        mid = (self.bid + self.ask) / 2.0
        return 0.0 if mid <= 0 else (self.ask - self.bid) / mid * 10_000.0


@dataclass(frozen=True, slots=True)
class VenueScore:
    venue: str
    score: float
    effective_price: float
    executable_qty: float
    expected_cost_bps: float
    reasons: tuple[str, ...]


class VenueScorer:
    """Ranks venues by executable cost, depth, latency and operational quality."""

    def __init__(
        self,
        *,
        latency_penalty_bps_per_ms: float = 0.002,
        reject_penalty_bps: float = 25.0,
        stale_penalty_bps_per_ms: float = 0.001,
        max_stale_ms: float = 2_000.0,
    ) -> None:
        self.latency_penalty_bps_per_ms = latency_penalty_bps_per_ms
        self.reject_penalty_bps = reject_penalty_bps
        self.stale_penalty_bps_per_ms = stale_penalty_bps_per_ms
        self.max_stale_ms = max_stale_ms

    def score(self, snapshot: VenueSnapshot, *, side: str, qty: float) -> VenueScore:
        if qty <= 0:
            raise ValueError("qty must be positive")
        side = side.lower()
        if side not in {"buy", "sell"}:
            raise ValueError("side must be buy or sell")
        if snapshot.bid <= 0 or snapshot.ask <= 0 or snapshot.ask < snapshot.bid:
            return VenueScore(snapshot.venue, -inf, inf, 0.0, inf, ("invalid-market",))
        if snapshot.stale_ms > self.max_stale_ms:
            return VenueScore(snapshot.venue, -inf, inf, 0.0, inf, ("stale-market",))

        price = snapshot.ask if side == "buy" else snapshot.bid
        available = snapshot.ask_size if side == "buy" else snapshot.bid_size
        executable = min(qty, max(0.0, available))
        if executable <= 0:
            return VenueScore(snapshot.venue, -inf, price, 0.0, inf, ("no-liquidity",))

        depth_penalty = max(0.0, qty / max(available, 1e-12) - 1.0) * 100.0
        latency_penalty = max(0.0, snapshot.latency_ms) * self.latency_penalty_bps_per_ms
        reject_penalty = max(0.0, min(1.0, snapshot.reject_rate)) * self.reject_penalty_bps
        stale_penalty = max(0.0, snapshot.stale_ms) * self.stale_penalty_bps_per_ms
        fee = snapshot.taker_fee_bps
        spread = snapshot.spread_bps / 2.0
        expected_cost = (
            fee + spread + depth_penalty + latency_penalty + reject_penalty + stale_penalty
        )
        score = -expected_cost

        reasons: list[str] = []
        if depth_penalty:
            reasons.append("depth-constrained")
        if snapshot.latency_ms > 50:
            reasons.append("high-latency")
        if snapshot.reject_rate > 0.01:
            reasons.append("reject-penalty")
        if snapshot.stale_ms > 250:
            reasons.append("stale-penalty")
        if not reasons:
            reasons.append("healthy")

        return VenueScore(snapshot.venue, score, price, executable, expected_cost, tuple(reasons))

    def rank(self, snapshots: list[VenueSnapshot], *, side: str, qty: float) -> list[VenueScore]:
        ranked = [self.score(snapshot, side=side, qty=qty) for snapshot in snapshots]
        return sorted(ranked, key=lambda item: item.score, reverse=True)
