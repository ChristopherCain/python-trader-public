# V5 patch notes

- Added execution kill switch for daily loss, venue reject bursts and stale market data.
- Added per-venue circuit breaker/failover state machine.
- Added deterministic retry policy.
- Added checksummed append-only execution journal and recovery summary.
- Added OMS/venue reconciliation diagnostics.
- Added transport-neutral WebSocket liveness supervisor.
- Added Binance Spot Test Network adapter restricted to the official testnet host.
- Added generated execution invariants and failure-path integration tests.
- Added reliability benchmark and CI coverage for the v5 paths.
- Corrected setuptools/CI paths for the repository's `src/` package layout.
