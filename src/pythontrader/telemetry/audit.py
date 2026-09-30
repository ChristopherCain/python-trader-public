import json
from pathlib import Path
from time import time


class AuditLog:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event: str, **fields):
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time(), "event": event, **fields}, sort_keys=True) + "\n")
