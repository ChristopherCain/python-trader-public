from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VWAPSlice:
    bucket: int
    qty: float


def vwap(total_qty: float, volume_profile: list[float]) -> list[VWAPSlice]:
    total = sum(max(0, x) for x in volume_profile)
    if total <= 0:
        return []
    return [VWAPSlice(i, total_qty * max(0, v) / total) for i, v in enumerate(volume_profile)]
