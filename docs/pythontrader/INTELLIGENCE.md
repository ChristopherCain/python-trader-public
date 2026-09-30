# Trading intelligence

`TradingBrain` is a small expert system rather than a single hard-coded strategy. Trend, mean-reversion, microstructure and volatility experts vote independently. Votes are confidence-weighted, a regime is inferred, and the resulting action is handed to an asset-aware execution planner.

The design allows additional models—forecasting, NLP, alternative data, cross-sectional ranking—to be registered without changing order/risk/accounting code. The autonomous orchestrator scans a heterogeneous universe through one interface and emits a complete decision record including expert consensus, confidence, regime and execution plan.
