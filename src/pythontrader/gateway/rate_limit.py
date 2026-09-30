from collections import deque


class SlidingRateLimiter:
    def __init__(self, limit: int, window_s: float):
        self.limit = limit
        self.window_s = window_s
        self.events = deque()

    def allow(self, now: float) -> bool:
        cutoff = now - self.window_s
        while self.events and self.events[0] < cutoff:
            self.events.popleft()
        if len(self.events) >= self.limit:
            return False
        self.events.append(now)
        return True
