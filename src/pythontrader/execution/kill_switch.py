from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum


class KillSwitchState(str, Enum):
    ARMED = "armed"
    TRIPPED = "tripped"


@dataclass(frozen=True, slots=True)
class KillSwitchSnapshot:
    state: KillSwitchState
    reason: str
    daily_pnl: float
    recent_rejects: int
    stale_feed_ms: float


class ExecutionKillSwitch:
    """Hard execution gate driven by loss, rejects and market-data freshness."""

    def __init__(
        self,
        *,
        max_daily_loss: float = 50_000.0,
        max_rejects_per_minute: int = 20,
        max_stale_feed_ms: float = 2_000.0,
    ) -> None:
        if max_daily_loss <= 0 or max_rejects_per_minute <= 0 or max_stale_feed_ms <= 0:
            raise ValueError("kill-switch limits must be positive")
        self.max_daily_loss = max_daily_loss
        self.max_rejects_per_minute = max_rejects_per_minute
        self.max_stale_feed_ms = max_stale_feed_ms
        self.state = KillSwitchState.ARMED
        self.reason = ""
        self.daily_pnl = 0.0
        self.stale_feed_ms = 0.0
        self._rejects: deque[float] = deque()

    def _trip(self, reason: str) -> None:
        if self.state is KillSwitchState.ARMED:
            self.state = KillSwitchState.TRIPPED
            self.reason = reason

    def record_pnl(self, pnl: float) -> None:
        self.daily_pnl = pnl
        if pnl <= -self.max_daily_loss:
            self._trip("daily-loss-limit")

    def record_reject(self, *, now: float) -> None:
        cutoff = now - 60.0
        while self._rejects and self._rejects[0] <= cutoff:
            self._rejects.popleft()
        self._rejects.append(now)
        if len(self._rejects) >= self.max_rejects_per_minute:
            self._trip("reject-burst")

    def record_feed_staleness(self, stale_ms: float) -> None:
        self.stale_feed_ms = max(0.0, stale_ms)
        if self.stale_feed_ms >= self.max_stale_feed_ms:
            self._trip("stale-market-data")

    def allow_execution(self) -> bool:
        return self.state is KillSwitchState.ARMED

    def reset(self) -> None:
        self.state = KillSwitchState.ARMED
        self.reason = ""
        self._rejects.clear()
        self.stale_feed_ms = 0.0

    def snapshot(self) -> KillSwitchSnapshot:
        return KillSwitchSnapshot(
            self.state,
            self.reason,
            self.daily_pnl,
            len(self._rejects),
            self.stale_feed_ms,
        )
