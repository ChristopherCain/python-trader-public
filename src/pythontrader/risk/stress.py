from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StressResult:
    name: str
    pnl: float


class StressEngine:
    def run(
        self, positions: dict[str, float], marks: dict[str, float], scenarios: dict[str, float]
    ) -> list[StressResult]:
        out = []
        for name, shock in scenarios.items():
            out.append(
                StressResult(name, sum(q * marks.get(s, 0) * shock for s, q in positions.items()))
            )
        return out
