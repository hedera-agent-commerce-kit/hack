"""
hack_pay.errors — Full error hierarchy for HACK.Pay.

All errors carry a machine-readable ``code`` string suitable for structured
logging and programmatic handling.  HTTP response bodies expose only the safe
top-level ``message`` — never internal detail, stack traces, or raw exception
text.
"""

from __future__ import annotations


class HackPayError(Exception):
    """Base class for all HACK.Pay errors."""

    code: str = "HACK_PAY_ERROR"

    def __init__(self, message: str = "", code: str | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code
        self.message = message

    def __repr__(self) -> str:
        return f"{type(self).__name__}(code={self.code!r}, message={self.message!r})"


# ── Configuration ─────────────────────────────────────────────────────────────

class ConfigurationError(HackPayError):
    """Raised at startup when required configuration is missing or invalid."""

    code = "CONFIGURATION_ERROR"


# ── Payment protocol errors ───────────────────────────────────────────────────

class PaymentError(HackPayError):
    """Base class for errors arising from the x402 payment protocol."""

    code = "PAYMENT_ERROR"


class MalformedPaymentError(PaymentError):
    """
    The PAYMENT-SIGNATURE header could not be decoded or parsed.

    Causes: invalid Base64, malformed JSON, missing required fields.
    """

    code = "MALFORMED_PAYMENT"


class UnsupportedProtocolVersionError(PaymentError):
    """
    The client sent an x402 v1 header (X-PAYMENT) instead of v2
    (PAYMENT-SIGNATURE).  Only v2 is supported.
    """

    code = "UNSUPPORTED_PROTOCOL_VERSION"


class InvalidPaymentError(PaymentError):
    """
    The payment proof was structurally valid but the facilitator rejected it.

    This covers signature verification failures and facilitator-level
    business-rule rejections.
    """

    code = "INVALID_PAYMENT"


class InsufficientPaymentError(PaymentError):
    """The payment amount is less than the required amount."""

    code = "INSUFFICIENT_PAYMENT"


class RecipientMismatchError(PaymentError):
    """
    The ``payTo`` field in the payment proof does not match the configured
    receiver account.
    """

    code = "RECIPIENT_MISMATCH"


class AssetMismatchError(PaymentError):
    """
    The asset in the payment proof does not match the configured asset
    (e.g. wrong HTS token entity ID).
    """

    code = "ASSET_MISMATCH"


class NetworkMismatchError(PaymentError):
    """
    The network in the payment proof does not match the configured network
    (e.g. mainnet proof presented to a testnet server).
    """

    code = "NETWORK_MISMATCH"


class ExpiredPaymentError(PaymentError):
    """
    The payment proof was submitted after ``max_deadline_seconds`` elapsed
    since the challenge was issued.
    """

    code = "EXPIRED_PAYMENT"


class OversizedPaymentHeaderError(PaymentError):
    """
    The PAYMENT-SIGNATURE header exceeds the 64 KB size limit.

    Enforced before any decoding to guard against decompression-bomb style
    attacks on the Base64 → JSON pipeline.
    """

    code = "OVERSIZED_PAYMENT_HEADER"

    def __init__(self, message: str = "PAYMENT-SIGNATURE header exceeds 64 KB limit") -> None:
        super().__init__(message)


# ── Facilitator errors ────────────────────────────────────────────────────────

class FacilitatorError(HackPayError):
    """
    Base class for errors arising from communication with the x402 facilitator.
    """

    code = "FACILITATOR_ERROR"


class FacilitatorUnavailableError(FacilitatorError):
    """The facilitator could not be reached (connection refused, DNS failure)."""

    code = "FACILITATOR_UNAVAILABLE"


class FacilitatorTimeoutError(FacilitatorError):
    """
    The facilitator did not respond within the configured timeout.

    Maps to HTTP 504 Gateway Timeout on the resource server.
    """

    code = "FACILITATOR_TIMEOUT"


class FacilitatorNetworkNotSupportedError(FacilitatorError):
    """
    The facilitator does not advertise support for the configured network +
    scheme combination (checked at startup via GET /supported).
    """

    code = "FACILITATOR_NETWORK_NOT_SUPPORTED"


class FacilitatorInvalidResponseError(FacilitatorError):
    """
    The facilitator returned a response that could not be parsed into the
    expected schema.
    """

    code = "FACILITATOR_INVALID_RESPONSE"


# ── Receipt errors ────────────────────────────────────────────────────────────

class ReceiptError(HackPayError):
    """Base class for errors arising from the receipt publication layer."""

    code = "RECEIPT_ERROR"


class DurableReceiptUnavailableError(ReceiptError):
    """
    ``require_durable_receipt=True`` is configured but the ReceiptPublisher
    backend is not available.

    The request is rejected rather than proceeding without a durable record.
    """

    code = "DURABLE_RECEIPT_UNAVAILABLE"
