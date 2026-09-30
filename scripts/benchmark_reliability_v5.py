from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from time import perf_counter

from pythontrader.execution.execution_journal import ExecutionJournal
from pythontrader.execution.oms import OrderManagementSystem
from pythontrader.execution.reconciliation import ExecutionReconciler, VenueOrderState
from pythontrader.execution.retry_policy import RetryPolicy
from pythontrader.execution.venue_failover import VenueFailoverManager


def run(iterations: int) -> dict[str, float | int | str]:
    retry = RetryPolicy()
    failover = VenueFailoverManager()
    reconciler = ExecutionReconciler()
    oms = OrderManagementSystem()

    start = perf_counter()
    checksum = ""
    with tempfile.TemporaryDirectory() as directory:
        journal = ExecutionJournal(Path(directory) / "journal.jsonl")
        for index in range(iterations):
            now = index * 0.001
            venue = f"v{index % 4}"
            if index % 97 == 0:
                failover.record_failure(venue, now=now)
            else:
                failover.record_success(venue, now=now)
            retry.decide(attempt=(index % 4) + 1, reason="timeout")
            if index % 50 == 0:
                record = journal.append("heartbeat", {"order_id": f"o{index}", "venue": venue})
                checksum = record.checksum
            if index % 200 == 0:
                reconciler.compare(oms, [VenueOrderState("external", "1", "accepted", 0.0)])
        records = len(tuple(journal.read()))
    elapsed = perf_counter() - start
    return {
        "schema": "pythontrader.reliability.benchmark.v1",
        "iterations": iterations,
        "elapsed_seconds": round(elapsed, 6),
        "operations_per_second": round(iterations / elapsed, 2) if elapsed else 0.0,
        "journal_records": records,
        "tail_checksum": checksum,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=50_000)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = run(args.iterations)
    print(json.dumps(result, indent=2, sort_keys=True) if args.json else result)


if __name__ == "__main__":
    main()
