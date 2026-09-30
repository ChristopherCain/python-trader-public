class StalenessWatchdog:
    def __init__(self, max_age_s: float):
        self.max_age_s = max_age_s
        self.last = {}

    def touch(self, key: str, ts: float):
        self.last[key] = ts

    def stale(self, now: float):
        return [k for k, v in self.last.items() if now - v > self.max_age_s]
