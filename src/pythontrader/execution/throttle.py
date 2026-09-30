from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from time import monotonic


@dataclass(frozen=True, slots=True)
class ThrottleDecision:
    allowed: bool
    retry_after_s: float
    reason: str


class OrderThrottle:
    """Per-venue and global sliding-window order-rate limiter."""

    def __init__(self, *, global_per_second: int = 100, per_venue_per_second: int = 30) -> None:
        if global_per_second <= 0 or per_venue_per_second <= 0:
            raise ValueError("limits must be positive")
        self.global_per_second = global_per_second
        self.per_venue_per_second = per_venue_per_second
        self._global: deque[float] = deque()
        self._venue: dict[str, deque[float]] = defaultdict(deque)

    @staticmethod
    def _prune(queue: deque[float], now: float) -> None:
        cutoff = now - 1.0
        while queue and queue[0] <= cutoff:
            queue.popleft()

    def check(
        self, venue: str, *, now: float | None = None, consume: bool = True
    ) -> ThrottleDecision:
        current = monotonic() if now is None else now
        self._prune(self._global, current)
        queue = self._venue[venue]
        self._prune(queue, current)

        if len(self._global) >= self.global_per_second:
            retry = max(0.0, 1.0 - (current - self._global[0]))
            return ThrottleDecision(False, retry, "global-rate-limit")
        if len(queue) >= self.per_venue_per_second:
            retry = max(0.0, 1.0 - (current - queue[0]))
            return ThrottleDecision(False, retry, "venue-rate-limit")

        if consume:
            self._global.append(current)
            queue.append(current)
        return ThrottleDecision(True, 0.0, "ok")
