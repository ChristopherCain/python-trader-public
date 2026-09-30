# Architecture
PythonTrader is organized around strict domain boundaries. Market-data adapters own transport concerns. `MarketCache` stores normalized state. `FeatureEngine` derives stable immutable snapshots. The ensemble converts those snapshots into a continuous score. `RiskEngine` is the final pre-trade authority. Accepted orders move through execution and only fills can mutate portfolio accounting.

## Data path
1. A feed emits normalized `Quote` objects.
2. `MarketCache` validates and updates each book and return ring.
3. `FeatureEngine` derives spread, imbalance, volatility and entropy.
4. Strategies independently score the feature snapshot.
5. `StrategyEnsemble` confidence-weights each opinion.
6. The engine maps consensus magnitude to intended quantity.
7. `RiskEngine` accepts, clips, or rejects the order.
8. Execution applies touch price, size-aware impact and fees.
9. `Portfolio` applies the fill and updates cash, position and realized PnL.
10. Metrics capture fills, rejects, consensus and marked equity.

The same domain objects are suitable for historical replay or a separately implemented live adapter because transport is intentionally outside accounting and risk.
