from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HealthCheck:
    name: str
    ok: bool
    detail: str = ""


class HealthRegistry:
    def __init__(self):
        self.checks = {}

    def set(self, name: str, ok: bool, detail: str = ""):
        self.checks[name] = HealthCheck(name, ok, detail)

    def overall(self):
        return all(c.ok for c in self.checks.values()) if self.checks else True

    def snapshot(self):
        return {n: {"ok": c.ok, "detail": c.detail} for n, c in self.checks.items()}
