"""
hack_pay.x402.codec — Encode and decode x402 v2 HTTP headers.

Pure functions, no I/O. Errors are subtypes of HackPayError so the
FastAPI adapter can map them to the correct HTTP status without catching
bare exceptions.
"""

from __future__ import annotations

import base64
import json

from hack_pay.errors import (
    MalformedPaymentError,
    OversizedPaymentHeaderError,
    UnsupportedProtocolVersionError,
)
from hack_pay.x402.types import PaymentPayload, PaymentRequirements, SettlementResponse

# 64 KB — enforced before any decode to block decompression-bomb payloads.
_MAX_HEADER_BYTES: int = 65_536


def encode_payment_required(req: PaymentRequirements) -> str:
    """Serialise PaymentRequirements → Base64(UTF-8 JSON) for PAYMENT-REQUIRED header."""
    return base64.b64encode(req.model_dump_json().encode()).decode()


def decode_payment_signature(header_value: str) -> PaymentPayload:
    """
    Parse a PAYMENT-SIGNATURE header value into a PaymentPayload.

    Raises
    ------
    OversizedPaymentHeaderError  — header exceeds 64 KB
    UnsupportedProtocolVersionError — x402_version != 2
    MalformedPaymentError        — bad Base64, bad JSON, or missing fields
    """
    if len(header_value.encode()) > _MAX_HEADER_BYTES:
        raise OversizedPaymentHeaderError()

    try:
        raw = base64.b64decode(header_value.encode(), validate=True)
    except Exception as exc:
        raise MalformedPaymentError(
            f"PAYMENT-SIGNATURE is not valid Base64: {exc}"
        ) from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise MalformedPaymentError(
            f"PAYMENT-SIGNATURE decoded to invalid JSON: {exc}"
        ) from exc

    # Reject v1 payloads with a clear message.
    version = data.get("x402Version") or data.get("x402_version")
    if version is not None and int(version) != 2:
        raise UnsupportedProtocolVersionError(
            f"x402 version {version} is not supported. Use x402_version=2."
        )

    try:
        return PaymentPayload.model_validate(data)
    except Exception as exc:
        raise MalformedPaymentError(
            f"PAYMENT-SIGNATURE has invalid structure: {exc}"
        ) from exc


def encode_payment_response(settlement: SettlementResponse) -> str:
    """Serialise SettlementResponse → Base64(UTF-8 JSON) for PAYMENT-RESPONSE header."""
    return base64.b64encode(settlement.model_dump_json().encode()).decode()


def extract_payment_signature_header(headers: dict[str, str]) -> str | None:
    """
    Return the PAYMENT-SIGNATURE header value, or None if absent.

    Raises UnsupportedProtocolVersionError if the v1 X-PAYMENT header is
    present — never silently fall back to v1.
    """
    lower = {k.lower(): v for k, v in headers.items()}

    if sig := lower.get("payment-signature"):
        return sig

    if lower.get("x-payment"):
        raise UnsupportedProtocolVersionError(
            "x402 v1 header 'X-PAYMENT' is not supported. "
            "Use 'PAYMENT-SIGNATURE' (x402 v2)."
        )

    return None