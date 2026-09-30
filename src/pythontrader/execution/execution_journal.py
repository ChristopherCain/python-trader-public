from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class JournalRecord:
    sequence: int
    kind: str
    payload: dict[str, Any]
    checksum: str


class ExecutionJournal:
    """Append-only JSONL journal with chained checksums for crash recovery."""

    def __init__(self, path: str | Path, *, fsync: bool = False) -> None:
        self.path = Path(path)
        self.fsync = fsync
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._sequence, self._checksum = self._tail_state()

    @staticmethod
    def _digest(sequence: int, kind: str, payload: dict[str, Any], previous: str) -> str:
        raw = json.dumps(
            {"sequence": sequence, "kind": kind, "payload": payload, "previous": previous},
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode()
        return hashlib.sha256(raw).hexdigest()

    def _tail_state(self) -> tuple[int, str]:
        records = list(self.read(validate=True)) if self.path.exists() else []
        if not records:
            return 0, ""
        tail = records[-1]
        return tail.sequence, tail.checksum

    def append(self, kind: str, payload: dict[str, Any]) -> JournalRecord:
        if not kind:
            raise ValueError("journal kind is required")
        sequence = self._sequence + 1
        checksum = self._digest(sequence, kind, payload, self._checksum)
        record = JournalRecord(sequence, kind, payload, checksum)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), sort_keys=True, default=str) + "\n")
            handle.flush()
            if self.fsync:
                os.fsync(handle.fileno())
        self._sequence = sequence
        self._checksum = checksum
        return record

    def read(self, *, validate: bool = True) -> Iterable[JournalRecord]:
        if not self.path.exists():
            return ()
        previous = ""
        rows: list[JournalRecord] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for expected, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                raw = json.loads(line)
                record = JournalRecord(
                    int(raw["sequence"]),
                    str(raw["kind"]),
                    dict(raw["payload"]),
                    str(raw["checksum"]),
                )
                if validate:
                    if record.sequence != expected:
                        raise ValueError("journal sequence gap")
                    digest = self._digest(record.sequence, record.kind, record.payload, previous)
                    if digest != record.checksum:
                        raise ValueError("journal checksum mismatch")
                previous = record.checksum
                rows.append(record)
        return tuple(rows)
