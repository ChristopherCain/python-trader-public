# PythonTrader v2 architecture

PythonTrader v2 replaces the earlier micro-module prototype with a smaller number of substantive subsystems. The core data path is:

`venue/replay -> L2 order book -> feature/context layer -> trading planner -> portfolio risk -> OMS -> deterministic execution -> portfolio/telemetry`.

## Stateful market microstructure

`pythontrader.marketdata.orderbook.OrderBook` maintains a sequence-checked L2 book, computes microprice and imbalance, exposes notional depth, and estimates market-order VWAP against visible depth. Sequence gaps are rejected rather than silently accepted.

## Order management

`pythontrader.execution.oms.OrderManagementSystem` owns order lifecycle state, partial fills, average fill price, fees, cancel/reject transitions, idempotent fill identifiers and deterministic L2 execution. Venue adapters can reuse the same state machine.

## Portfolio risk

`pythontrader.risk.portfolio_engine.PortfolioRiskEngine` evaluates gross/net exposure, leverage, symbol limits, sector concentration, asset-class caps, daily loss and liquidity constraints before execution. It also exposes historical/parametric VaR and deterministic stress calculations.

## Asset-specific models

Perpetual futures include funding, basis, maintenance margin, liquidation approximation and crowding/carry signals. Memecoin risk uses liquidity-to-market-cap, holder/deployer concentration, turnover, unique trader activity and pool age to produce a bounded quality score and maximum position fraction.

## Decision planner

`TradingPlanner` combines independent expert votes while keeping alpha, confidence, position fraction and execution style separate. Perps receive funding/basis/crowding experts; memecoins receive a quality gate; equities/FX/spot use market-specific execution policies.

## Replay and benchmarking

The deterministic replay harness generates a repeatable market stream, runs planner -> risk -> OMS -> fills, and emits a checksum. This lets CI catch behavioral drift without depending on external venues.
