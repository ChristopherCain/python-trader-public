# Changelog
## 0.9.0
- Introduced event-driven engine and normalized domain model.
- Added strategy ensemble, pre-trade risk controls, execution simulator and portfolio accounting.
- Added deterministic synthetic venue, market-making model, persistence, API, telemetry and backtesting.
- Added Go latency probe and TypeScript API client.

## 1.2.0
- Added universal asset universe: equities, ETFs, FX, crypto, memecoins, perpetuals, futures, indices, commodities and options analytics.
- Added autonomous expert-system brain and cross-asset scanner.
- Added asset-specific risk/execution models, public market-data venue adapters and universal API.
- Added dedicated perpetual and memecoin models plus new integration tests.

## 1.3.0

- Added an async event runtime with bounded backpressure and delivery accounting.
- Added Kraken and Yahoo read-only market-data adapters plus a freshness-aware router.
- Added machine-readable deterministic benchmark output (`pythontrader.benchmark.v1`).
- Added Python 3.11/3.12/3.13 CI matrix with Ruff, mypy, pytest and coverage.
- Replaced the web scaffolding with a read-only API client instead of a duplicated backend tree.
- Consolidated packaging on the root `pyproject.toml`.

## 1.5.0

- Added execution kill switch, deterministic retry policy and per-venue circuit breakers.
- Added checksummed append-only execution journal, recovery summaries and OMS/venue reconciliation.
- Added WebSocket stream liveness supervision and stale-feed integration controls.
- Added Binance Spot Test Network adapter restricted to the official testnet endpoint.
- Added generated routing invariants, failure-path integration tests and reliability benchmark.
- Corrected setuptools and CI paths for the `src/pythontrader` package layout.
