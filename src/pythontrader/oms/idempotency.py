class IdempotencyCache:
    def __init__(self, capacity: int = 10000):
        self.capacity = capacity
        self.keys = []
        self.values = {}

    def put(self, key: str, value):
        if key in self.values:
            return self.values[key]
        self.values[key] = value
        self.keys.append(key)
        if len(self.keys) > self.capacity:
            old = self.keys.pop(0)
            self.values.pop(old, None)
        return value

    def get(self, key: str):
        return self.values.get(key)
