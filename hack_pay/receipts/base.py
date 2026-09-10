"""
hack_pay.receipts.base — ReceiptPublisher abstract interface.

The default implementation (NoopReceiptPublisher) does nothing.
Future implementations: HcsReceiptPublisher, DatabaseReceiptPublisher.

Contract
--------
- publish() must not raise on transient backend failure unless the
  application sets require_durable_receipt=True on the endpoint.
- is_available() is called before publish() when require_durable=True.
- Implementations must be safe for concurrent async calls.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from hack_pay.receipts.types import PaymentReceipt


class ReceiptPublisher(ABC):
    """Abstract base for durable receipt recording backends."""

    @abstractmethod
    async def publish(self, receipt: PaymentReceipt) -> None:
        """
        Durably record a settled payment receipt.

        Must not raise on transient failure unless require_durable=True is
        enforced by the caller.
        """

    @abstractmethod
    async def is_available(self) -> bool:
        """Return True if the backend is reachable right now."""
