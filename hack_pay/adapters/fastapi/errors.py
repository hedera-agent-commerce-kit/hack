"""
hack_pay.adapters.fastapi.errors — Map HackPayError to HTTP responses.

Rules
-----
- Never include internal error messages, stack traces, or raw exception
  text in HTTP response bodies.
- Only the safe, generic message string is returned to the client.
- The x402Version field is always included so clients know the protocol.
"""

from __future__ import annotations

from fastapi.responses import JSONResponse

from hack_pay.errors import (
    AssetMismatchError,
    DurableReceiptUnavailableError,
    ExpiredPaymentError,
    FacilitatorError,
    FacilitatorTimeoutError,
    HackPayError,
    InsufficientPaymentError,
    InvalidPaymentError,
    MalformedPaymentError,
    NetworkMismatchError,
    OversizedPaymentHeaderError,
    RecipientMismatchError,
    UnsupportedProtocolVersionError,
)

# Maps error type → (http_status, safe_client_message)
_ERROR_MAP: dict[type[HackPayError], tuple[int, str]] = {
    InsufficientPaymentError: (402, "Insufficient payment"),
    InvalidPaymentError: (402, "Invalid payment proof"),
    MalformedPaymentError: (402, "Malformed payment header"),
    RecipientMismatchError: (402, "Payment recipient mismatch"),
    AssetMismatchError: (402, "Payment asset mismatch"),
    NetworkMismatchError: (402, "Payment network mismatch"),
    ExpiredPaymentError: (402, "Payment proof expired"),
    UnsupportedProtocolVersionError: (402, "Unsupported x402 version; use v2"),
    OversizedPaymentHeaderError: (400, "Payment header too large"),
    FacilitatorTimeoutError: (504, "Payment facilitator timeout"),
    FacilitatorError: (502, "Payment facilitator error"),
    DurableReceiptUnavailableError: (503, "Receipt service unavailable"),
}


def error_to_response(error: HackPayError) -> JSONResponse:
    """
    Convert a HackPayError to a safe JSONResponse.

    The response body contains only the safe client message and the
    x402Version — never internal detail or tracebacks.
    """
    status, message = _ERROR_MAP.get(type(error), (502, "Payment error"))
    return JSONResponse(
        status_code=status,
        content={"error": message, "x402Version": 2},
    )
