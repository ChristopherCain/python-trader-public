from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass(slots=True)
class VenueHealth:
    venue: str
    state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    last_failure_at: float = 0.0
    last_success_at: float = 0.0


class VenueFailoverManager:
    """Circuit breaker and venue eligibility registry for execution failover."""

    def __init__(self, *, failure_threshold: int = 3, cooldown_s: float = 5.0) -> None:
        if failure_threshold < 1 or cooldown_s < 0:
            raise ValueError("invalid failover configuration")
        self.failure_threshold = failure_threshold
        self.cooldown_s = cooldown_s
        self._health: dict[str, VenueHealth] = {}

    def _item(self, venue: str) -> VenueHealth:
        return self._health.setdefault(venue, VenueHealth(venue))

    def record_success(self, venue: str, *, now: float) -> VenueHealth:
        item = self._item(venue)
        item.state = CircuitState.CLOSED
        item.consecutive_failures = 0
        item.last_success_at = now
        return item

    def record_failure(self, venue: str, *, now: float) -> VenueHealth:
        item = self._item(venue)
        item.consecutive_failures += 1
        item.last_failure_at = now
        if item.consecutive_failures >= self.failure_threshold:
            item.state = CircuitState.OPEN
        return item

    def eligible(self, venue: str, *, now: float) -> bool:
        item = self._item(venue)
        if item.state is CircuitState.CLOSED:
            return True
        if item.state is CircuitState.OPEN and now - item.last_failure_at >= self.cooldown_s:
            item.state = CircuitState.HALF_OPEN
            return True
        return item.state is CircuitState.HALF_OPEN

    def healthy_venues(self, venues: list[str], *, now: float) -> list[str]:
        return [venue for venue in venues if self.eligible(venue, now=now)]

    def snapshot(self) -> dict[str, dict[str, object]]:
        return {
            venue: {
                "state": item.state.value,
                "consecutive_failures": item.consecutive_failures,
                "last_failure_at": item.last_failure_at,
                "last_success_at": item.last_success_at,
            }
            for venue, item in sorted(self._health.items())
        }
