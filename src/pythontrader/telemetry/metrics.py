from collections import defaultdict, deque


class Metrics:
    def __init__(self, window: int = 5000):
        self.counters = defaultdict(int)
        self.gauges = {}
        self.series = defaultdict(lambda: deque(maxlen=window))

    def inc(self, name: str, n: int = 1):
        self.counters[name] += n

    def set(self, name: str, value: float):
        self.gauges[name] = float(value)

    def observe(self, name: str, value: float):
        self.series[name].append(float(value))

    def snapshot(self):
        return {
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "series": {k: list(v) for k, v in self.series.items()},
        }
