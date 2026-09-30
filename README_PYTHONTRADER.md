# PythonTrader

**PythonTrader** is a universal autonomous trading-research and market-making system. Its backend is built around a single idea: one intelligence layer should be able to reason over very different markets without pretending that equities, FX, perpetuals and thin memecoins have the same microstructure.

The repository contains an executable multi-market backend: normalized market data, a heterogeneous instrument registry, strategy/expert ensemble, regime inference, cross-asset risk, portfolio accounting, smart execution planning, OMS primitives, market-making, research/backtesting, persistence, telemetry, FastAPI control plane, TypeScript client and a small Go latency probe.

> The public repository ships with deterministic execution simulation and read-only public market-data adapters. Broker/exchange order-entry credentials are not bundled. This keeps the complete decision/risk/accounting backend runnable without representing simulated fills as external executions.

## Markets

PythonTrader understands the semantics of:

- **US equities and ETFs** — session/liquidity-aware execution, ADV-style participation controls.
- **FX** — pip-aware spot-pair calculations and spread-sensitive routing.
- **Spot crypto** — 24/7 instruments and fragmented-venue execution planning.
- **Memecoins** — separate fragility/liquidity/concentration model for thin reflexive markets.
- **Perpetual futures** — mark/index basis, funding carry, leverage and liquidation primitives.
- **Listed futures** — tick size, lot size and contract multiplier aware exposure.
- **Commodities and indices** — cross-asset signals, hedging/reference inputs and volatility budgets.
- **Options analytics** — Black–Scholes pricing plus delta/gamma/vega primitives.

## Autonomous decision path

```text
        ┌────────────── heterogeneous universe ──────────────┐
        │ equities · FX · crypto · memes · perps · futures │
        └─────────────────────────┬──────────────────────────┘
                                  ▼
                         Venue / Feed Layer
                                  │
                                  ▼
                         Normalized Quotes
                                  │
                                  ▼
             ┌────────────── Trading Brain ────────────────┐
             │ trend · mean reversion · microstructure    │
             │ volatility · regime · relative value      │
             └────────────────────┬────────────────────────┘
                                  ▼
                       Opportunity / Consensus
                                  │
                    ┌─────────────┴──────────────┐
                    ▼                            ▼
             Cross-Asset Risk             Execution Planner
                    │                   POV/VWAP/IOC/post-only
                    └─────────────┬──────────────┘
                                  ▼
                               OMS
                                  ▼
                         Execution Harness
                                  ▼
                    Portfolio / Audit / Metrics
```

## Backend subsystems

- `pythontrader/autonomy/` — universal autonomous scanner/orchestrator.
- `pythontrader/intelligence/` — expert voting, regime inference and decision records.
- `pythontrader/universe/` — heterogeneous instrument metadata and discovery registry.
- `pythontrader/venues/` — venue capabilities, normalized adapters and public-data connectors.
- `pythontrader/asset_models/` — perp, equity, FX, memecoin and options-specific mechanics.
- `pythontrader/strategies/` — momentum, mean reversion, liquidity, volatility, entropy, pairs, funding carry, cross-asset and meme momentum.
- `pythontrader/risk/` — pre-trade limits, VaR/stress, leverage, liquidity and cross-asset concentration.
- `pythontrader/execution/` — matching, impact/fees, TWAP/VWAP/POV and asset-aware universal planning.
- `pythontrader/market_making/` — Avellaneda–Stoikov quoting and inventory controls.
- `pythontrader/portfolio/` — positions, cash, PnL, marked equity and exposure analytics.
- `pythontrader/oms/` and `orders/` — lifecycle, idempotency and order state.
- `pythontrader/research/` / `backtest/` — rolling statistics, cointegration, bootstrap, replay and walk-forward tools.
- `pythontrader/storage/` — SQLite event journal and atomic checkpoints.
- `pythontrader/telemetry/` / `monitoring/` — metrics, audit events, health and watchdogs.
- `pythontrader/api/` — FastAPI control plane including universal-market endpoints.

## Quick start

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows
# .venv\Scripts\activate
pip install -e .[dev]
pytest
python -m pythontrader.cli run --steps 5000
uvicorn pythontrader.api.app:app --reload
```

Universal scanner endpoints:

```text
GET  /v1/universal/status
GET  /v1/universal/universe
GET  /v1/universal/venues
POST /v1/universal/scan
```

A scan traverses the full configured universe, produces normalized quotes, derives microstructure/statistical features, runs an expert consensus, classifies regime and generates an asset-specific execution plan.

## Example: autonomous scan

```python
from pythontrader.autonomy import AutonomousTrader

trader = AutonomousTrader()
rows = trader.scan_once()
for x in rows:
    print(x["symbol"], x["asset_class"], x["action"], x["score"], x["execution"]["style"])
```

## Perpetuals

Perpetuals are not treated as generic spot crypto. The backend has mark/index basis, funding carry, open-interest state, leverage budgets and liquidation-price helpers. Execution plans switch between maker/taker behavior based on urgency and can represent reduce-only semantics.

## Memecoins

Memecoins have their own risk surface. Liquidity, top-holder concentration and age feed a fragility score; fragility reduces both allowed notional and directional signal strength. That keeps the rest of the system universal without flattening every market into the same model.

## Public market-data adapters

`venues/coinbase_public.py` and `venues/binance_public.py` demonstrate normalized read-only market-data connectors. They use the same `Quote` contract as `SyntheticUniversalVenue`, so external data can be swapped in without touching intelligence, risk or portfolio code.

## Testing

The suite covers portfolio accounting, execution matching, protocols, security helpers, scheduler, market making, risk, storage, the original engine and the newer universal-market layer. Run:

```bash
pytest -q
```

## Documentation

- `docs/ARCHITECTURE.md` — core event/data flow.
- `docs/UNIVERSAL_MARKETS.md` — asset-class and venue abstraction.
- `docs/INTELLIGENCE.md` — expert consensus and regime inference.
- `docs/PERPS.md` — perpetual-futures mechanics.
- `docs/MEMECOINS.md` — thin-market controls.
- `docs/RISK.md`, `docs/MARKET_MAKING.md`, `docs/OPERATIONS.md`, `docs/DEVELOPMENT.md` — subsystem details.

PythonTrader is deliberately backend-heavy: the web surface is a control plane over executable state rather than a static trading mockup.


## V2 substantive backend

The v2 backend consolidates the prototype into stateful production-style components: a sequence-checked L2 order book, OMS with idempotent fills and partial-fill accounting, portfolio risk with asset-class caps and VaR/stress primitives, perpetual and memecoin-specific market models, an asset-aware trading planner, and deterministic replay/benchmark tooling. See `docs/V2_ARCHITECTURE.md`.

Run `python scripts/benchmark_v2.py` for a deterministic end-to-end replay benchmark.

## v1.3 repository maturity

The current tree uses a single root `pyproject.toml`, a Python 3.11–3.13 CI matrix, Ruff/mypy/pytest/coverage gates, a machine-readable deterministic benchmark, read-only public market-data adapters and an API-only web client. `web/` contains no duplicated backend implementation.

Useful checks:

```bash
pip install -e '.[dev]'
ruff check pythontrader tests scripts
mypy pythontrader
pytest --cov=pythontrader --cov-report=term-missing
python scripts/benchmark_json.py --events 100000 --seed 1337 --output artifacts/benchmark.json
```

See `docs/V3_MATURITY.md` for the maturity pass and repository invariants.

## v1.5 execution reliability

V5 adds failure-aware execution primitives: a hard kill switch, per-venue circuit breakers, deterministic retry policy, checksummed execution journal, restart recovery summaries, OMS/venue reconciliation, stream heartbeat supervision and a Binance Spot Test Network adapter restricted to the official testnet endpoint.

```bash
PYTHONPATH=src pytest -q
PYTHONPATH=src python scripts/benchmark_reliability_v5.py --iterations 50000 --json
```

See `docs/V5_RELIABILITY.md`. Testnet support is sandbox-only and is not presented as evidence of live-money execution.
