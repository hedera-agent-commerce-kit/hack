"""
hack_pay.idempotency.memory — In-memory IdempotencyStore.

Suitable for development and single-process deployments.
NOT suitable for multi-process production (use Redis or PostgreSQL instead).

Process restart behaviour: all keys are lost.  The facilitator-level
idempotency guard prevents double-settlement on restart.

Capacity: bounded by max_entries.  When the limit is hit, expired entries
are evicted first.  If no expired entries exist, the store silently stops
accepting new keys (existing cached receipts remain accessible).
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from hack_pay.idempotency.base import IdempotencyStore
from hack_pay.receipts.types import PaymentReceipt


@dataclass
class _Entry:
    receipt: PaymentReceipt
    expires_at: float  # monotonic clock seconds


class InMemoryIdempotencyStore(IdempotencyStore):
    """Thread-safe in-memory idempotency store backed by asyncio.Lock."""

    def __init__(self, max_entries: int = 10_000) -> None:
        self._store: dict[str, _Entry] = {}
        self._lock = asyncio.Lock()
        self._max_entries = max_entries

    async def get(self, key: str) -> PaymentReceipt | None:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if time.monotonic() > entry.expires_at:
                del self._store[key]
                return None
            return entry.receipt

    async def put(
        self,
        key: str,
        receipt: PaymentReceipt,
        ttl_seconds: int = 3600,
    ) -> None:
        async with self._lock:
            self._evict_expired()
            if len(self._store) < self._max_entries:
                self._store[key] = _Entry(receipt, time.monotonic() + ttl_seconds)

    async def put_if_absent(
        self,
        key: str,
        receipt: PaymentReceipt,
        ttl_seconds: int = 3600,
    ) -> PaymentReceipt:
        async with self._lock:
            entry = self._store.get(key)
            if entry is not None and time.monotonic() <= entry.expires_at:
                return entry.receipt  # concurrent caller already stored
            self._evict_expired()
            if len(self._store) < self._max_entries:
                self._store[key] = _Entry(receipt, time.monotonic() + ttl_seconds)
            return receipt

    def _evict_expired(self) -> None:
        now = time.monotonic()
        expired = [k for k, v in self._store.items() if v.expires_at <= now]
        for k in expired:
            del self._store[k]

    @property
    def size(self) -> int:
        """Current number of live entries (for testing / metrics)."""
        return len(self._store)