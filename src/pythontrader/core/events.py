from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Event:
    topic: str
    payload: Any
    ts: float


class EventBus:
    def __init__(self, history: int = 2048):
        self._subs: dict[str, list[Callable[[Event], None]]] = defaultdict(list)
        self._history = deque(maxlen=history)

    def subscribe(self, topic: str, fn: Callable[[Event], None]) -> None:
        self._subs[topic].append(fn)

    def publish(self, event: Event) -> None:
        self._history.append(event)
        for fn in tuple(self._subs.get(event.topic, ())):
            fn(event)
        for fn in tuple(self._subs.get("*", ())):
            fn(event)

    def recent(self, topic: str | None = None) -> list[Event]:
        return [e for e in self._history if topic is None or e.topic == topic]
