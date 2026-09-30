# PythonTrader v1.3 maturity pass

The v1.3 pass focuses on repository coherence rather than file count.

## Packaging

The repository has one canonical `pyproject.toml`. Development dependencies include Ruff, mypy, pytest and coverage. The supported runtime matrix is Python 3.11–3.13.

## Runtime

`pythontrader.core.runtime.EventRuntime` provides ordered async event dispatch, bounded backpressure, per-handler delivery accounting and deterministic sequence identifiers. It is shared by integration tests and can be used by service processes without introducing hidden threads.

## Market data

Public adapters are deliberately read-only. `KrakenPublicClient` normalizes ticker data into the common `Quote` contract; `YahooPublicClient` exposes reference equity/ETF pricing without fabricating L1 depth. `MarketDataRouter` adds source registration, validation, caching and controlled stale fallback.

## Reproducible benchmark

`python scripts/benchmark_json.py --events 100000 --seed 1337 --output artifacts/benchmark.json`

The result is machine-readable and contains the schema version, seed, event count, accepted/rejected orders, fill count, elapsed time, throughput, latency percentiles and a deterministic replay checksum.

## Web client

`web/` is a thin client of the FastAPI control plane. It does not contain a second copy of backend Python modules. Backend code remains canonical under `pythontrader/` / `src/pythontrader/` depending on checkout layout.

## Development process

Future work should use short-lived feature branches and pull requests. Branches and PRs are development workflow artifacts; they should be created for actual changes rather than reconstructed retroactively.
