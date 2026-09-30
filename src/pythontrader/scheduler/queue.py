import heapq
from dataclasses import dataclass, field


@dataclass(order=True)
class ScheduledTask:
    run_at: float
    name: str = field(compare=False)
    payload: dict = field(compare=False, default_factory=dict)


class TaskQueue:
    def __init__(self):
        self.q = []

    def put(self, t: ScheduledTask):
        heapq.heappush(self.q, t)

    def due(self, now: float):
        out = []
        while self.q and self.q[0].run_at <= now:
            out.append(heapq.heappop(self.q))
        return out
