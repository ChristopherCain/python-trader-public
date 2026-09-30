from dataclasses import dataclass
from time import time


class Clock:
    def now(self) -> float:
        return time()


@dataclass(slots=True)
class ManualClock(Clock):
    value: float = 0.0

    def now(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds
