from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class StreamState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    LIVE = "live"
    BACKOFF = "backoff"


@dataclass(frozen=True, slots=True)
class StreamSnapshot:
    state: StreamState
    reconnects: int
    last_message_at: float
    stale_for_s: float


class WebSocketSupervisor:
    """Transport-neutral heartbeat/reconnect state machine for venue streams."""

    def __init__(self, *, stale_after_s: float = 5.0, max_backoff_s: float = 30.0) -> None:
        if stale_after_s <= 0 or max_backoff_s <= 0:
            raise ValueError("stream thresholds must be positive")
        self.stale_after_s = stale_after_s
        self.max_backoff_s = max_backoff_s
        self.state = StreamState.DISCONNECTED
        self.reconnects = 0
        self.last_message_at = 0.0

    def connecting(self) -> None:
        self.state = StreamState.CONNECTING

    def connected(self, *, now: float) -> None:
        self.state = StreamState.LIVE
        self.last_message_at = now

    def message(self, *, now: float) -> None:
        self.state = StreamState.LIVE
        self.last_message_at = now

    def heartbeat(self, *, now: float) -> bool:
        if self.state is StreamState.LIVE and now - self.last_message_at >= self.stale_after_s:
            self.state = StreamState.BACKOFF
            self.reconnects += 1
            return False
        return self.state is StreamState.LIVE

    def backoff_s(self) -> float:
        return min(self.max_backoff_s, 0.25 * (2 ** max(0, self.reconnects - 1)))

    def snapshot(self, *, now: float) -> StreamSnapshot:
        stale = max(0.0, now - self.last_message_at) if self.last_message_at else 0.0
        return StreamSnapshot(self.state, self.reconnects, self.last_message_at, stale)
