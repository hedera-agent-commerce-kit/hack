"""
hack_pay.idempotency.redis — Redis-backed IdempotencyStore.

Suitable for multi-process and containerised production deployments.

Requires the optional ``hack-pay[redis]`` extra::

    pip install hack-pay[redis]

Atomicity
---------
``put_if_absent`` uses a single ``SET key value NX PX ttl_ms`` command.
This is atomic at the Redis level — no Lua script or WATCH/MULTI needed.
Exactly one caller across all processes will receive the NX write; all
others will read back the already-stored receipt.

Key format
----------
All keys are prefixed with ``_KEY_PREFIX`` so they are namespaced within
a shared Redis instance and the prefix can be changed in one place.
"""

from __future__ import annotations

import dataclasses
import json
from datetime import datetime
from typing import Any

from hack_pay.idempotency.base import IdempotencyStore
from hack_pay.receipts.types import PaymentReceipt

try:
    from redis.asyncio import Redis
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "RedisIdempotencyStore requires the 'redis' package. "
        "Install it with: pip install hack-pay[redis]"
    ) from exc

_KEY_PREFIX = "hack_pay:idempotency:"


def _full_key(key: str) -> str:
    return f"{_KEY_PREFIX}{key}"


def _serialize(receipt: PaymentReceipt) -> str:
    d: dict[str, Any] = dataclasses.asdict(receipt)
    d["settled_at"] = receipt.settled_at.isoformat()
    return json.dumps(d)


def _deserialize(raw: str) -> PaymentReceipt:
    d = json.loads(raw)
    d["settled_at"] = datetime.fromisoformat(d["settled_at"])
    return PaymentReceipt(**d)


class RedisIdempotencyStore(IdempotencyStore):
    """
    Production-ready idempotency store backed by Redis.

    Safe for concurrent async access across multiple processes.

    Parameters
    ----------
    client:
        An initialised ``redis.asyncio.Redis`` instance.
        The caller is responsible for its lifecycle (connect / close).
    """

    def __init__(self, client: Redis) -> None:
        self._redis = client

    async def get(self, key: str) -> PaymentReceipt | None:
        raw = await self._redis.get(_full_key(key))
        if raw is None:
            return None
        return _deserialize(raw if isinstance(raw, str) else raw.decode())

    async def put(
        self,
        key: str,
        receipt: PaymentReceipt,
        ttl_seconds: int = 3600,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError(f"ttl_seconds must be positive, got {ttl_seconds}")
        await self._redis.set(_full_key(key), _serialize(receipt), ex=ttl_seconds)

    async def put_if_absent(
        self,
        key: str,
        receipt: PaymentReceipt,
        ttl_seconds: int = 3600,
    ) -> PaymentReceipt:
        """
        Atomically store receipt only if key is absent (SET NX PX).

        Returns the receipt now stored — either the one just inserted,
        or the pre-existing one if another process won the race.
        """
        if ttl_seconds <= 0:
            raise ValueError(f"ttl_seconds must be positive, got {ttl_seconds}")
        full_key = _full_key(key)
        ttl_ms = ttl_seconds * 1000
        serialized = _serialize(receipt)
        stored = await self._redis.set(full_key, serialized, nx=True, px=ttl_ms)
        if stored:
            return receipt
        # Another process won — fetch and return what is stored.
        raw = await self._redis.get(full_key)
        if raw is not None:
            return _deserialize(raw if isinstance(raw, str) else raw.decode())
        # Key expired between our failed SET NX and GET — retry once.
        stored = await self._redis.set(full_key, serialized, nx=True, px=ttl_ms)
        if stored:
            return receipt
        raw = await self._redis.get(full_key)
        if raw is not None:
            return _deserialize(raw if isinstance(raw, str) else raw.decode())
        # Extremely unlikely: expired again after second attempt — return our receipt.
        return receipt
