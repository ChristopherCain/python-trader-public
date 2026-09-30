# PythonTrader v5 — execution reliability and testnet readiness

V5 moves the execution subsystem from routing-only behavior toward failure-aware operation.

## Reliability components

- **ExecutionKillSwitch** — hard gate for daily-loss, reject-burst and stale-feed thresholds.
- **VenueFailoverManager** — per-venue circuit breaker with open/half-open/closed states.
- **RetryPolicy** — deterministic capped exponential backoff for transient venue errors.
- **ExecutionJournal** — append-only JSONL journal with sequence validation and chained SHA-256 checksums.
- **ExecutionRecovery** — deterministic reconstruction summary from the journal.
- **ExecutionReconciler** — compares local OMS state with venue-reported open orders/fills.
- **WebSocketSupervisor** — transport-neutral heartbeat and reconnect state machine.

## Testnet connector

`BinanceSpotTestnetAdapter` is deliberately restricted to `https://testnet.binance.vision`.
Signed order/cancel calls require credentials supplied by the caller and never read secrets from disk.
The adapter is intended for sandbox integration tests, not evidence of live-money trading.

## Validation

V5 adds generated invariant coverage for routing quantity conservation, reliability unit tests,
and an integration test covering stale-stream -> kill-switch -> venue-failover behavior.

```bash
PYTHONPATH=src pytest -q
PYTHONPATH=src python scripts/benchmark_reliability_v5.py --iterations 50000 --json
```
