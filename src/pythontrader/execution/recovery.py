from __future__ import annotations

from dataclasses import dataclass

from pythontrader.execution.execution_journal import ExecutionJournal


@dataclass(frozen=True, slots=True)
class RecoveryState:
    records: int
    submitted: frozenset[str]
    terminal: frozenset[str]
    last_sequence: int
    checksum: str


class ExecutionRecovery:
    """Builds a deterministic recovery summary from the append-only execution journal."""

    def recover(self, journal: ExecutionJournal) -> RecoveryState:
        records = tuple(journal.read(validate=True))
        submitted: set[str] = set()
        terminal: set[str] = set()
        for record in records:
            order_id = str(record.payload.get("order_id", ""))
            if not order_id:
                continue
            if record.kind in {"submitted", "accepted", "replace-submitted"}:
                submitted.add(order_id)
            if record.kind in {"filled", "canceled", "rejected"}:
                terminal.add(order_id)
        last_sequence = records[-1].sequence if records else 0
        checksum = records[-1].checksum if records else ""
        return RecoveryState(
            len(records), frozenset(submitted), frozenset(terminal), last_sequence, checksum
        )
