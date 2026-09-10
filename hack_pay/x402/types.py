"""
hack_pay.x402.types — x402 v2 wire protocol types.

These are the exact Python equivalents of the x402 v2 JSON wire shapes.
This module is intentionally pure: no HTTP, no blockchain, no I/O.
Pydantic is used for validation and JSON serialisation.

References
----------
- x402 spec: https://x402.org
- Hedera exact scheme: https://docs.hedera.com/solutions/ai/x402/exact-scheme
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator


class PaymentRequirements(BaseModel):
    """
    Advertised by the resource server in the ``PAYMENT-REQUIRED`` header.

    The client reads this to know where to send funds, how much, and which
    facilitator fee-payer to include in the transaction.

    Hedera-specific notes
    ---------------------
    - ``network`` uses CAIP-2 identifiers: ``"hedera:testnet"`` or
      ``"hedera:mainnet"``.
    - ``amount`` is a decimal string of tinybars (1 HBAR = 100_000_000 tinybars).
    - ``asset`` is ``"0.0.0"`` for native HBAR, or an HTS fungible token entity
      ID (e.g. ``"0.0.6001"``) for token payments.
    - ``extra["feePayer"]`` must contain the facilitator fee-payer account ID
      (e.g. ``"0.0.7162784"``).  The client includes this as the transaction
      fee payer when building the partially-signed ``TransferTransaction``.
    """

    scheme: str = Field(..., description="Payment scheme, e.g. 'exact'")
    network: str = Field(..., description="CAIP-2 network identifier")
    pay_to: str = Field(..., description="Hedera account ID of the receiver")
    amount: str = Field(..., description="Amount in tinybars as a decimal string")
    asset: str = Field(
        default="0.0.0",
        description="Asset identifier: '0.0.0' for HBAR, HTS entity ID for tokens",
    )
    description: str = Field(default="", description="Human-readable endpoint description")
    mime_type: str = Field(default="", description="MIME type of the protected resource")
    max_deadline_seconds: int = Field(
        default=300,
        ge=1,
        description="Seconds after challenge issuance within which payment is accepted",
    )
    extra: dict[str, Any] = Field(
        default_factory=dict,
        description="Scheme-specific extras; Hedera uses {'feePayer': '0.0.XXXXX'}",
    )

    model_config = {"frozen": True}

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive_integer_string(cls, v: str) -> str:
        if not re.fullmatch(r"[1-9][0-9]*", v):
            raise ValueError(
                f"amount must be a canonical positive decimal integer string "
                f"(no leading zeros, spaces, signs, or underscores), got {v!r}"
            )
        return v

    @field_validator("network")
    @classmethod
    def network_must_be_hedera(cls, v: str) -> str:
        if not v.startswith("hedera:"):
            raise ValueError(
                f"network must be a Hedera CAIP-2 identifier (e.g. 'hedera:testnet'), got {v!r}"
            )
        return v


class PaymentPayload(BaseModel):
    """
    Sent by the client in the ``PAYMENT-SIGNATURE`` header.

    ``payload`` is a Base64-encoded, partially-signed Hedera
    ``TransferTransaction``.  The facilitator adds its fee-payer signature,
    submits the transaction, and awaits ``SUCCESS`` before returning a
    ``SettlementResponse``.
    """

    x402_version: int = Field(default=2, description="x402 protocol version; must be 2")
    scheme: str = Field(..., description="Payment scheme, must match requirements.scheme")
    network: str = Field(..., description="CAIP-2 network identifier")
    payload: str = Field(
        ...,
        description="Base64-encoded partially-signed Hedera TransferTransaction bytes",
    )

    model_config = {"frozen": True}

    @field_validator("x402_version")
    @classmethod
    def version_must_be_two(cls, v: int) -> int:
        if v != 2:
            raise ValueError(f"x402_version must be 2, got {v}")
        return v


class SettlementResponse(BaseModel):
    """
    Returned by the facilitator after ``POST /settle``.

    Echoed back to the client in the ``PAYMENT-RESPONSE`` header on a
    successful 200 response.
    """

    success: bool = Field(..., description="True if the transaction was submitted and confirmed")
    transaction: str | None = Field(
        default=None,
        description="Hedera transaction ID, e.g. '0.0.12345@1725000000.000000000'",
    )
    network: str | None = Field(default=None, description="CAIP-2 network the tx was settled on")
    payer: str | None = Field(default=None, description="Payer account ID extracted from tx")
    error: str | None = Field(default=None, description="Error message if success=False")

    model_config = {"frozen": True}
