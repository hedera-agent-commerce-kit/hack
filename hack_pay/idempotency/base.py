"""
hack_pay.idempotency.base — IdempotencyStore abstract interface.

Replay semantics
----------------
- First call with key K: get() returns None → caller proceeds to settle.
- Concurrent duplicate (race condition): put_if_absent() is atomic — exactly
  one caller stores; the other receives the already-stored receipt.
- Subsequent replays: get() returns cached receipt → skip verify+settle.
- After TTL expiry: key is evicted; next call is treated as new.
  This is safe because the facilitator has its own idempotency guard that
  prevents double-settlement at the network level even if the in-process
  store is cleared.

Implementations must be safe for concurrent async access.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from hack_pay.receipts.types import PaymentReceipt


class IdempotencyStore(ABC):
    """Abstract idempotency store for settled payment receipts."""

    @abstractmethod
    async def get(self, key: str) -> PaymentReceipt | None:
        """Return the cached receipt for key, or None if not found / expired."""

    @abstractmethod
    async def put(
        self,
        key: str,
        receipt: PaymentReceipt,
        ttl_seconds: int = 3600,
    ) -> None:
        """Store receipt under key with a TTL."""

    @abstractmethod
    async def put_if_absent(
        self,
        key: str,
        receipt: PaymentReceipt,
        ttl_seconds: int = 3600,
    ) -> PaymentReceipt:
        """
        Atomically store receipt only if key is absent.

        Returns the receipt that is now stored — either the one just inserted,
        or the pre-existing one if a concurrent caller won the race.
        This guarantees that concurrent duplicate payments result in exactly
        one settlement being recorded.
        """
