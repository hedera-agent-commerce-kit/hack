"""
hack_pay.providers.base — PaymentProvider interface + VerifyResult/SettleResult.

Dependency rule: NO imports from fastapi, starlette, httpx, or any chain SDK.
Only hack_pay.x402.types and hack_pay.errors are allowed here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from hack_pay.x402.types import PaymentPayload, PaymentRequirements


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    reason: str = ""

    @classmethod
    def success(cls) -> VerifyResult:
        return cls(ok=True)

    @classmethod
    def failure(cls, reason: str) -> VerifyResult:
        return cls(ok=False, reason=reason)


@dataclass(frozen=True)
class SettleResult:
    ok: bool
    transaction_id: str = ""
    payer: str | None = None
    receiver: str | None = None
    reason: str = ""

    @classmethod
    def success(
        cls,
        transaction_id: str,
        payer: str | None = None,
        receiver: str | None = None,
    ) -> SettleResult:
        return cls(ok=True, transaction_id=transaction_id, payer=payer, receiver=receiver)

    @classmethod
    def failure(cls, reason: str) -> SettleResult:
        return cls(ok=False, reason=reason)


class PaymentProvider(ABC):
    """
    Abstraction over a payment network + facilitator pair.

    All implementations must be safe for concurrent async calls after
    initialize() completes successfully.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """
        One-time startup: fetch /supported, cache feePayer, validate config.
        Raises ConfigurationError or FacilitatorError on failure.
        """

    @abstractmethod
    async def build_payment_requirements(
        self,
        config: object,  # PaymentConfig — forward ref avoids circular import
    ) -> PaymentRequirements:
        """Build PaymentRequirements for the 402 challenge response."""

    @abstractmethod
    async def verify(
        self,
        payload: PaymentPayload,
        requirements: PaymentRequirements,
    ) -> VerifyResult:
        """Validate the signed payment proof. Does NOT submit to network."""

    @abstractmethod
    async def settle(
        self,
        payload: PaymentPayload,
        requirements: PaymentRequirements,
    ) -> SettleResult:
        """Co-sign, submit, and await SUCCESS. Must be facilitator-idempotent."""

    @abstractmethod
    async def close(self) -> None:
        """Release resources (e.g. close HTTP client)."""
