# v4 execution patch

Adds a stateful multi-venue execution layer:

- venue cost/quality scoring
- size-aware slippage estimation
- multi-venue smart order routing
- IOC vs passive child-order selection
- per-venue/global throttling
- deterministic cancel/replace
- end-to-end execution coordinator
- execution benchmark with JSON output
- focused execution tests

This patch is additive and does not require fabricated broker fills or live-order claims.
