import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Settings:
    starting_cash: float = 1_000_000.0
    max_gross_exposure: float = 1_500_000.0
    max_symbol_exposure: float = 150_000.0
    max_order_notional: float = 50_000.0
    max_daily_loss: float = 35_000.0
    participation_rate: float = 0.10
    mm_inventory_limit: float = 2500.0
    telemetry_window: int = 5000
    seed: int = 7
    mode: str = "simulation"

    @classmethod
    def load(cls, path: str | Path | None = None) -> "Settings":
        if not path:
            return cls()
        data = json.loads(Path(path).read_text())
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**known)
