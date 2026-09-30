# Universal market layer

PythonTrader treats venue connectivity and instrument semantics as separate concerns. Every symbol is described by `InstrumentRegistry`; every feed implements the same quote contract; every decision passes through a shared intelligence, risk and execution-planning pipeline.

| Market | Model | Distinct controls |
|---|---|---|
| Equities / ETFs | session + liquidity | ADV participation, halt/borrow context |
| FX | spot pair | pip-aware sizing and spread logic |
| Spot crypto | 24x7 spot | venue sweep / fragmentation aware |
| Memecoins | thin spot | fragility, concentration, liquidity caps |
| Perpetuals | leveraged derivative | mark/index basis, funding, leverage, reduce-only |
| Futures | contract derivative | multiplier, tick value, contract-aware exposure |
| Commodities | spot/future proxy | commodity-specific volatility budget |
| Indices | reference instruments | cross-asset state and hedging inputs |
| Options | analytical layer | Black-Scholes price plus delta/gamma/vega |

The bundled public HTTP adapters are market-data-only. They deliberately share the same normalized `Quote` object as the deterministic venue so research and integration tests do not depend on external connectivity.
