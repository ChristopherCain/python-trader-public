# Risk subsystem
Risk is checked synchronously before an order reaches execution. Limits are explicit values, not hidden constants. `max_order` limits each instruction, `max_symbol` controls concentration, `max_gross` caps total absolute marked exposure and `max_daily_loss` switches the engine into a locked state once violated. Oversize orders can be clipped rather than discarded when a safe residual quantity exists.

`historical_var` and `parametric_var` are reporting analytics and are intentionally separated from the hard pre-trade gate. `StressEngine` applies deterministic shocks to marked positions so scenario results remain auditable.
