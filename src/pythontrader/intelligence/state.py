from dataclasses import dataclass, field


@dataclass(slots=True)
class WorldState:
    regime: str = "unknown"
    risk_budget: float = 1.0
    stress: float = 0.0
    opportunities: dict = field(default_factory=dict)
    correlations: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
