"""
hack_pay.providers.hedera.types — Facilitator API response types.

These mirror the JSON shapes returned by Blocky402 and x402.org facilitators
on GET /supported, POST /verify, and POST /settle.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SupportedKind(BaseModel):
    """One entry in the GET /supported response."""

    scheme: str = Field(..., description="Payment scheme, e.g. 'exact'")
    network: str = Field(..., description="CAIP-2 network identifier")
    # Blocky402 and x402.org return feePayer (camelCase) in their response
    fee_payer: str | None = Field(
        default=None,
        alias="feePayer",
        description="Hedera fee-payer account ID sponsored by this facilitator",
    )

    model_config = {"populate_by_name": True}


class FacilitatorSupportedResponse(BaseModel):
    """Response body from GET /supported."""

    kinds: list[SupportedKind] = Field(default_factory=list)


class FacilitatorVerifyResponse(BaseModel):
    """Response body from POST /verify."""

    is_valid: bool = Field(..., alias="isValid")
    error: str | None = Field(default=None)
    # Some facilitators return invalidReason instead of error
    invalid_reason: str | None = Field(default=None, alias="invalidReason")

    model_config = {"populate_by_name": True}

    @property
    def failure_reason(self) -> str:
        """Best available failure reason string."""
        return self.error or self.invalid_reason or "Facilitator rejected payment"
