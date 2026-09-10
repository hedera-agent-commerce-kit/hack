"""
hack_pay.receipts.types — PaymentReceipt value type.

Contains only fields that are directly justified by the x402 settlement
response.  No speculative fields, no registry data, no HCS anchoring
(that is an optional future publisher).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PaymentReceipt:
    """
    Immutable record of a successfully settled x402 payment.

    All fields come directly from the facilitator settlement response or
    from the PaymentRequirements the server issued — never from
    client-supplied request data.

    Attributes
    ----------
    transaction_id:
        Hedera transaction ID returned by the facilitator after the
        TransferTransaction reached SUCCESS, e.g.
        ``"0.0.12345@1725000000.000000000"``.
    payer_account_id:
        Hedera account ID of the payer, if the facilitator returns it.
        May be None for facilitators that do not expose this field.
    receiver_account_id:
        The ``pay_to`` account from PaymentRequirements — always set.
    amount_tinybars:
        Exact integer tinybars settled on-chain.
    asset:
        Asset identifier: ``"0.0.0"`` for native HBAR.
    network:
        CAIP-2 network identifier, e.g. ``"hedera:testnet"``.
    settled_at:
        UTC datetime at which HACK.Pay received the settlement confirmation.
    facilitator_url:
        Base URL of the facilitator that processed the payment.
        Useful for auditing which facilitator was in the payment path.
    """

    transaction_id: str
    payer_account_id: str | None
    receiver_account_id: str
    amount_tinybars: int
    asset: str
    network: str
    settled_at: datetime
    facilitator_url: str
