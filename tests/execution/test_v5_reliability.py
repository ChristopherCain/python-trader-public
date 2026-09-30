from pathlib import Path

import pytest

from pythontrader.domain import Fill, Order, OrderType, Side
from pythontrader.execution.execution_journal import ExecutionJournal
from pythontrader.execution.kill_switch import ExecutionKillSwitch, KillSwitchState
from pythontrader.execution.oms import OrderManagementSystem
from pythontrader.execution.reconciliation import (
    ExecutionReconciler,
    ReconciliationIssue,
    VenueOrderState,
)
from pythontrader.execution.recovery import ExecutionRecovery
from pythontrader.execution.retry_policy import RetryPolicy
from pythontrader.execution.venue_failover import CircuitState, VenueFailoverManager


def test_retry_policy_is_capped_and_deterministic():
    policy = RetryPolicy(max_attempts=4, base_delay_s=0.1, max_delay_s=0.25)
    assert policy.decide(attempt=1, reason="timeout").delay_s == 0.1
    assert policy.decide(attempt=2, reason="timeout").delay_s == 0.2
    assert policy.decide(attempt=3, reason="timeout").delay_s == 0.25
    assert not policy.decide(attempt=4, reason="timeout").retry
    assert not policy.decide(attempt=1, reason="invalid-order").retry


def test_kill_switch_trips_on_daily_loss():
    switch = ExecutionKillSwitch(max_daily_loss=100)
    switch.record_pnl(-100)
    assert switch.state is KillSwitchState.TRIPPED
    assert switch.reason == "daily-loss-limit"
    assert not switch.allow_execution()


def test_kill_switch_trips_on_reject_burst():
    switch = ExecutionKillSwitch(max_rejects_per_minute=3)
    switch.record_reject(now=10)
    switch.record_reject(now=20)
    switch.record_reject(now=30)
    assert switch.snapshot().reason == "reject-burst"


def test_venue_failover_opens_and_half_opens_after_cooldown():
    manager = VenueFailoverManager(failure_threshold=2, cooldown_s=5)
    manager.record_failure("alpha", now=1)
    item = manager.record_failure("alpha", now=2)
    assert item.state is CircuitState.OPEN
    assert not manager.eligible("alpha", now=6.9)
    assert manager.eligible("alpha", now=7.0)
    assert manager.snapshot()["alpha"]["state"] == "half_open"
    manager.record_success("alpha", now=8)
    assert manager.snapshot()["alpha"]["state"] == "closed"


def test_execution_journal_roundtrip_and_recovery(tmp_path: Path):
    journal = ExecutionJournal(tmp_path / "execution.jsonl")
    journal.append("submitted", {"order_id": "o1"})
    journal.append("accepted", {"order_id": "o1"})
    journal.append("filled", {"order_id": "o1", "qty": 5})
    records = tuple(journal.read())
    assert [r.sequence for r in records] == [1, 2, 3]
    assert len({r.checksum for r in records}) == 3
    recovered = ExecutionRecovery().recover(journal)
    assert recovered.records == 3
    assert recovered.submitted == frozenset({"o1"})
    assert recovered.terminal == frozenset({"o1"})


def test_execution_journal_detects_tampering(tmp_path: Path):
    path = tmp_path / "execution.jsonl"
    journal = ExecutionJournal(path)
    journal.append("submitted", {"order_id": "o1"})
    text = path.read_text()
    path.write_text(text.replace('"o1"', '"evil"'))
    with pytest.raises(ValueError, match="checksum"):
        tuple(ExecutionJournal(path).read())


def test_reconciler_finds_status_and_fill_mismatch():
    oms = OrderManagementSystem()
    order = Order("o1", "XYZ", Side.BUY, 10, OrderType.LIMIT, limit_price=100)
    oms.submit(order)
    oms.accept("o1", "venue-1")
    oms.apply_fill("f1", Fill("o1", "XYZ", Side.BUY, 4, 99.5, 0.1, "alpha", 1.0))
    diffs = ExecutionReconciler().compare(
        oms,
        [VenueOrderState("o1", "venue-1", "filled", 10.0)],
    )
    kinds = {diff.issue for diff in diffs}
    assert ReconciliationIssue.STATUS_MISMATCH in kinds
    assert ReconciliationIssue.FILLED_QTY_MISMATCH in kinds


def test_reconciler_detects_venue_only_order():
    diffs = ExecutionReconciler().compare(
        OrderManagementSystem(),
        [VenueOrderState("foreign", "v1", "accepted", 0.0)],
    )
    assert len(diffs) == 1
    assert diffs[0].issue is ReconciliationIssue.VENUE_ONLY
