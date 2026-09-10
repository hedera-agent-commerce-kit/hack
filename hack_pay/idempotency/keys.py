"""
hack_pay.idempotency.keys — Idempotency key derivation.

The key is a SHA-256 digest of the raw TransferTransaction bytes extracted
from the PaymentPayload.  This makes the key:

- Stable across retries (same payment proof → same key)
- Independent of header encoding variations
- Resistant to key collisions (SHA-256 collision resistance)
"""

from __future__ import annotations

import base64
import hashlib

from hack_pay.x402.types import PaymentPayload


def derive_idempotency_key(payload: PaymentPayload) -> str:
    """
    Return a hex-encoded SHA-256 digest of the raw transaction bytes.

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
    return hashlib.sha256(raw_bytes).hexdigest()
