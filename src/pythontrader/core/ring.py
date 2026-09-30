from collections import deque
from statistics import fmean


class NumericRing:
    def __init__(self, size: int):
        self.data = deque(maxlen=size)

    def push(self, x: float) -> None:
        self.data.append(float(x))

    def mean(self) -> float:
        return fmean(self.data) if self.data else 0.0

    def last(self, n: int | None = None) -> list[float]:
        d = list(self.data)
        return d if n is None else d[-n:]

    def __len__(self) -> int:
        return len(self.data)
