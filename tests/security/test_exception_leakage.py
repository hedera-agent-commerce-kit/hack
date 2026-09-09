"""tests/security/test_exception_leakage.py — Error responses must not leak internals."""

import pytest
from hack_pay.adapters.fastapi.errors import error_to_response
from hack_pay.errors import (
    FacilitatorError, FacilitatorTimeoutError, HackPayError,
    InsufficientPaymentError, InvalidPaymentError, MalformedPaymentError,
)


class TestExceptionLeakage:
    def _assert_safe_response(self, error: HackPayError) -> None:
        resp = error_to_response(error)
        body = resp.body.decode()
        # Must not contain Python traceback markers
        assert "Traceback" not in body
        assert "File \"" not in body
        assert "line " not in body
        # Must not contain raw exception message (internal detail)
        assert error.message not in body or error.message == ""
        # Must contain x402Version
        assert "x402Version" in body

    def test_invalid_payment_error_safe(self):
        self._assert_safe_response(
            InvalidPaymentError("internal detail: sig mismatch at byte 42")
        )

    def test_facilitator_error_safe(self):
        self._assert_safe_response(
            FacilitatorError("connection refused to 10.0.0.1:4020")
        )

    def test_facilitator_timeout_safe(self):
        self._assert_safe_response(FacilitatorTimeoutError("timeout after 10s"))

    def test_malformed_error_safe(self):
        self._assert_safe_response(
            MalformedPaymentError("JSON parse error at position 42")
        )

    def test_all_known_errors_map_to_expected_status_codes(self):
        from hack_pay.errors import (
            AssetMismatchError, NetworkMismatchError, RecipientMismatchError,
            OversizedPaymentHeaderError, DurableReceiptUnavailableError,
        )
        cases = [
            (InvalidPaymentError("x"), 402),
            (InsufficientPaymentError("x"), 402),
            (MalformedPaymentError("x"), 402),
            (AssetMismatchError("x"), 402),
            (NetworkMismatchError("x"), 402),
            (RecipientMismatchError("x"), 402),
            (OversizedPaymentHeaderError(), 400),
            (FacilitatorError("x"), 502),
            (FacilitatorTimeoutError("x"), 504),
            (DurableReceiptUnavailableError("x"), 503),
        ]
        for error, expected_status in cases:
            resp = error_to_response(error)
            assert resp.status_code == expected_status, \
                f"{type(error).__name__} → expected {expected_status}, got {resp.status_code}"