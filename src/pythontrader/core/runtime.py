from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from time import monotonic, time
from typing import Any

Handler = Callable[["RuntimeEvent"], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class RuntimeEvent:
    topic: str
    payload: Any
    ts: float = field(default_factory=time)
    sequence: int = 0


@dataclass(frozen=True, slots=True)
class RuntimeStats:
    published: int
    delivered: int
    failed: int
    queue_depth: int
    uptime_s: float


class EventRuntime:
    """Small deterministic async event runtime used by integration/replay paths.

    The runtime owns topic subscriptions, monotonically increasing sequence IDs,
    bounded backpressure and handler accounting. It intentionally avoids hidden
    background threads so the same component can be used in tests, replays and
    service processes.
    """

    def __init__(self, *, max_queue: int = 10_000) -> None:
        if max_queue <= 0:
            raise ValueError("max_queue must be positive")
        self._queue: asyncio.Queue[RuntimeEvent] = asyncio.Queue(maxsize=max_queue)
        self._handlers: defaultdict[str, list[Handler]] = defaultdict(list)
        self._sequence = 0
        self._published = 0
        self._delivered = 0
        self._failed = 0
        self._started_at = monotonic()
        self._closed = False

    def subscribe(self, topic: str, handler: Handler) -> Callable[[], None]:
        if not topic:
            raise ValueError("topic is required")
        self._handlers[topic].append(handler)

        def unsubscribe() -> None:
            handlers = self._handlers.get(topic)
            if handlers and handler in handlers:
                handlers.remove(handler)

        return unsubscribe

    async def publish(self, topic: str, payload: Any, *, ts: float | None = None) -> RuntimeEvent:
        if self._closed:
            raise RuntimeError("runtime is closed")
        self._sequence += 1
        event = RuntimeEvent(
            topic=topic, payload=payload, ts=time() if ts is None else ts, sequence=self._sequence
        )
        await self._queue.put(event)
        self._published += 1
        return event

    async def dispatch_one(self) -> RuntimeEvent | None:
        if self._queue.empty():
            return None
        event = await self._queue.get()
        try:
            handlers = [*self._handlers.get(event.topic, ()), *self._handlers.get("*", ())]
            for handler in handlers:
                try:
                    await handler(event)
                    self._delivered += 1
                except Exception:
                    self._failed += 1
                    raise
            return event
        finally:
            self._queue.task_done()

    async def drain(self, *, limit: int | None = None) -> int:
        processed = 0
        while not self._queue.empty() and (limit is None or processed < limit):
            await self.dispatch_one()
            processed += 1
        return processed

    async def close(self) -> None:
        await self._queue.join()
        self._closed = True

    def stats(self) -> RuntimeStats:
        return RuntimeStats(
            published=self._published,
            delivered=self._delivered,
            failed=self._failed,
            queue_depth=self._queue.qsize(),
            uptime_s=max(0.0, monotonic() - self._started_at),
        )
