SCENARIOS = {
    "flash_crash": {"equity": -0.12, "crypto": -0.20, "fx": 0.015},
    "risk_on": {"equity": 0.05, "crypto": 0.09, "fx": -0.005},
    "vol_shock": {"equity": -0.04, "crypto": -0.08, "fx": 0.01},
}


def shock_for(name: str, asset_class: str) -> float:
    return SCENARIOS.get(name, {}).get(asset_class, 0.0)
