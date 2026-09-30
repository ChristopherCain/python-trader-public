import json
import os
import tempfile
from pathlib import Path


class CheckpointStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, state: dict):
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=self.path.name)
        os.close(fd)
        Path(tmp).write_text(json.dumps(state, sort_keys=True))
        os.replace(tmp, self.path)

    def load(self) -> dict:
        return json.loads(self.path.read_text()) if self.path.exists() else {}
