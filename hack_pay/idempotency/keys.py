"""
hack_pay.idempotency.keys — Idempotency key derivation.

The key is a SHA-256 digest of the raw TransferTransaction bytes and the
server's payment requirements. This makes the key:

- Stable across retries with the same payment terms
- Bound to amount, asset, recipient, network, and scheme
- Independent of header encoding variations
- Resistant to key collisions (SHA-256 collision resistance)
"""

from __future__ import annotations

import base64
import hashlib
import json

from hack_pay.x402.types import PaymentPayload, PaymentRequirements


def derive_idempotency_key(
    payload: PaymentPayload,
    requirements: PaymentRequirements,
) -> str:
    """
    Return a hex-encoded SHA-256 digest bound to the current requirements.

    Parameters
    ----------
    payload:
        The decoded PaymentPayload from the PAYMENT-SIGNATURE header.

    Returns
    -------
    str
        64-character lowercase hex string.
    """
    raw_bytes = base64.b64decode(payload.payload)
    binding = json.dumps(
        {
            "amount": requirements.amount,
            "asset": requirements.asset,
            "network": requirements.network,
            "pay_to": requirements.pay_to,
            "scheme": requirements.scheme,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(raw_bytes + b"\x00" + binding).hexdigest()
