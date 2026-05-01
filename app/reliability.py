import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar


T = TypeVar("T")


class CircuitBreakerOpen(RuntimeError):
    pass


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int
    reset_seconds: float
    failures: int = 0
    opened_until: float = 0

    def before_call(self) -> None:
        if self.opened_until > time.monotonic():
            raise CircuitBreakerOpen(f"{self.name} circuit is temporarily open")

    def record_success(self) -> None:
        self.failures = 0
        self.opened_until = 0

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.opened_until = time.monotonic() + self.reset_seconds


async def retry_with_backoff(
    operation: Callable[[], Awaitable[T]],
    *,
    attempts: int,
    initial_backoff_seconds: float,
    backoff_multiplier: float,
    circuit_breaker: CircuitBreaker | None = None,
) -> T:
    last_error: Exception | None = None
    delay = initial_backoff_seconds

    for attempt in range(1, attempts + 1):
        try:
            if circuit_breaker:
                circuit_breaker.before_call()
            result = await operation()
            if circuit_breaker:
                circuit_breaker.record_success()
            return result
        except Exception as exc:
            last_error = exc
            if circuit_breaker:
                circuit_breaker.record_failure()
            if attempt == attempts:
                break
            await asyncio.sleep(delay)
            delay *= backoff_multiplier

    assert last_error is not None
    raise last_error
