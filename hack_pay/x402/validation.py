"""
hack_pay.x402.validation — Structural validators for x402 wire types.

These validators are called by PaymentGate before forwarding a payment proof
to the provider.  They catch obvious mismatches (wrong network, wrong asset,
wrong recipient) without making any network calls.
"""

from __future__ import annotations

from hack_pay.errors import (
    AssetMismatchError,
    NetworkMismatchError,
    RecipientMismatchError,
)
from hack_pay.x402.types import PaymentPayload, PaymentRequirements


def validate_payload_matches_requirements(
    payload: PaymentPayload,
    requirements: PaymentRequirements,
) -> None:
    """
    Verify that the client-supplied PaymentPayload is consistent with the
    PaymentRequirements the server issued.

    Raises
    ------
    NetworkMismatchError   — payload.network != requirements.network
    AssetMismatchError     — scheme mismatch (future: asset field check)
    RecipientMismatchError — not raised here (checked post-settlement)

    Notes
    -----
    Amount and recipient validation happens at the facilitator level during
    /verify.  We only cross-check fields the server itself controls here.
    """
    if payload.network != requirements.network:
        raise NetworkMismatchError(
            f"Payment network mismatch: proof is for {payload.network!r} "
            f"but server requires {requirements.network!r}."
        )

    if payload.scheme != requirements.scheme:
        raise AssetMismatchError(
            f"Payment scheme mismatch: proof uses {payload.scheme!r} "
            f"but server requires {requirements.scheme!r}."
        )


def validate_settlement_recipient(
    transaction_pay_to: str | None,
    expected_receiver: str,
) -> None:
    """
    After settlement, assert the on-chain recipient matches configuration.

    Called with the ``pay_to`` extracted from the facilitator settlement
    response.  If the facilitator does not return the pay_to field this
    check is skipped (not all facilitator implementations return it).

    Raises
    ------
    RecipientMismatchError — pay_to present but does not match expected_receiver
    """
    if transaction_pay_to is None:
        return
    if transaction_pay_to != expected_receiver:
        raise RecipientMismatchError(
            f"Settlement recipient mismatch: tx paid to {transaction_pay_to!r} "
            f"but server expected {expected_receiver!r}."
        )