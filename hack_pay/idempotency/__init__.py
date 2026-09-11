"""hack_pay.idempotency — Idempotency store interface and implementations."""

from hack_pay.idempotency.base import IdempotencyStore
from hack_pay.idempotency.memory import InMemoryIdempotencyStore

__all__ = ["IdempotencyStore", "InMemoryIdempotencyStore", "RedisIdempotencyStore"]


def __getattr__(name: str) -> object:
    if name == "RedisIdempotencyStore":
        from hack_pay.idempotency.redis import RedisIdempotencyStore
        return RedisIdempotencyStore
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
