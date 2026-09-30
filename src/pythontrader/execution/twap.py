from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Slice:
    index: int
    qty: float
    release_s: float


def twap(total_qty: float, duration_s: float, slices: int) -> list[Slice]:
    if slices <= 0:
        raise ValueError("slices")
    q = total_qty / slices
    step = duration_s / slices
    return [Slice(i, q, i * step) for i in range(slices)]
