from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Window:
    train_start: int
    train_end: int
    test_start: int
    test_end: int


def windows(n: int, train: int, test: int, step: int | None = None):
    step = step or test
    i = 0
    while i + train + test <= n:
        yield Window(i, i + train, i + train, i + train + test)
        i += step
