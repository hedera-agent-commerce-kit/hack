"""hack_pay.receipts.noop — No-op ReceiptPublisher (default)."""

from __future__ import annotations

from hack_pay.receipts.base import ReceiptPublisher
from hack_pay.receipts.types import PaymentReceipt


class NoopReceiptPublisher(ReceiptPublisher):
    """
    Default ReceiptPublisher that discards receipts.

    Use this when durable receipt recording is not required.
    For production auditability, replace with a real implementation
    (e.g. HcsReceiptPublisher once HCS support is added).
    """

    async def publish(self, receipt: PaymentReceipt) -> None:
        pass  # intentional no-op

    async def is_available(self) -> bool:
        return True
