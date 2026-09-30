from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RetryDecision:
    retry: bool
    delay_s: float
    attempt: int
    reason: str


class RetryPolicy:
    """Deterministic capped exponential backoff for venue operations."""

    def __init__(
        self,
        *,
        max_attempts: int = 4,
        base_delay_s: float = 0.05,
        max_delay_s: float = 1.0,
        retryable_reasons: frozenset[str] | None = None,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if base_delay_s < 0 or max_delay_s < base_delay_s:
            raise ValueError("invalid retry delay configuration")
        self.max_attempts = max_attempts
        self.base_delay_s = base_delay_s
        self.max_delay_s = max_delay_s
        self.retryable_reasons = retryable_reasons or frozenset(
            {"timeout", "temporarily-unavailable", "rate-limit", "connection-reset"}
        )

    def decide(self, *, attempt: int, reason: str) -> RetryDecision:
        if attempt < 1:
            raise ValueError("attempt must be >= 1")
        if reason not in self.retryable_reasons:
            return RetryDecision(False, 0.0, attempt, "non-retryable")
        if attempt >= self.max_attempts:
            return RetryDecision(False, 0.0, attempt, "attempts-exhausted")
        delay = min(self.max_delay_s, self.base_delay_s * (2 ** (attempt - 1)))
        return RetryDecision(True, delay, attempt, "retry")
