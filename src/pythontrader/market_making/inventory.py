class InventoryController:
    def __init__(self, limit: float):
        self.limit = abs(limit)

    def skew(self, inventory: float) -> float:
        return max(-1, min(1, -inventory / self.limit)) if self.limit else 0.0

    def allowed(self, inventory: float, delta: float) -> bool:
        return abs(inventory + delta) <= self.limit
