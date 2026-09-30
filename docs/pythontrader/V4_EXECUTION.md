# PythonTrader v4 Execution Layer

The v4 execution stack turns parent orders into measurable multi-venue routing decisions instead of treating execution as a single simulated fill.

## Pipeline

`Parent Order -> Venue snapshots -> VenueScorer -> SlippageModel -> OrderThrottle -> SmartOrderRouter -> Child orders -> OMS -> Execution report`

### VenueScorer

Ranks venues using executable top-of-book liquidity, taker fees, spread, latency, stale-market penalties and recent reject rate. Invalid or stale markets are excluded from routing.

### SmartOrderRouter

Splits a parent order across up to four venues with a per-venue allocation cap. Low urgency produces passive limit children; high urgency uses IOC children. Each child retains an expected-cost estimate in basis points.

### SlippageModel

Uses spread plus square-root market impact, volatility and participation penalties to make routing costs size-aware.

### OrderThrottle

Maintains global and per-venue one-second sliding windows. Routing can skip a venue that is currently over the configured request rate.

### Cancel/replace

`CancelReplaceManager` preserves already-filled quantity constraints and refuses to replace terminal orders or change symbol/side.

### ExecutionCoordinator

Connects the router to the deterministic OMS and L2 replay book for end-to-end execution tests. The coordinator deliberately uses the simulator/replay path; write-capable broker connectivity remains a separate adapter concern.

## Reproducible benchmark

```bash
PYTHONPATH=src python scripts/benchmark_execution_v4.py --iterations 25000 --json
```

The benchmark emits machine-readable routing throughput and p50/p95 route latency rather than hard-coded performance claims.
