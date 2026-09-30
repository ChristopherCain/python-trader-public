def participation_schedule(
    observed_volumes: list[float], rate: float, max_clip: float
) -> list[float]:
    if not 0 <= rate <= 1:
        raise ValueError("rate")
    return [min(max_clip, max(0, v) * rate) for v in observed_volumes]
