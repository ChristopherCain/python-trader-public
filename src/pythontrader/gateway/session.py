from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from time import time


class SessionState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    READY = "ready"
    DEGRADED = "degraded"


@dataclass(slots=True)
class GatewaySession:
    name: str
    state: SessionState = SessionState.DISCONNECTED
    connected_at: float | None = None
    last_heartbeat: float | None = None
    errors: list[str] = field(default_factory=list)

    def connect(self):
        self.state = SessionState.READY
        self.connected_at = time()
        self.last_heartbeat = self.connected_at

    def heartbeat(self):
        self.last_heartbeat = time()

    def fail(self, message: str):
        self.errors.append(message)
        self.state = SessionState.DEGRADED
