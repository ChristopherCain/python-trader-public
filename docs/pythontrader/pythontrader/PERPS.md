# Perpetual futures

The perpetual layer tracks mark/index basis, funding, open interest and leverage. `PerpState.carry_signal` expresses funding pressure; `funding_carry` blends funding and basis into a normalized relative-value signal. Liquidation-price utilities and leverage budgets are asset-specific primitives available to risk policies.
