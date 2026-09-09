"""tests/security/test_oversized_headers.py — Header size limits."""

import pytest
from hack_pay.errors import OversizedPaymentHeaderError
from hack_pay.x402.codec import decode_payment_signature


class TestOversizedHeaders:
    def test_header_exceeding_64kb_raises(self):
        oversized = "A" * 70_000
        with pytest.raises(OversizedPaymentHeaderError):
            decode_payment_signature(oversized)

    def test_header_at_64kb_limit_raises(self):
        at_limit = "A" * 65_536
        with pytest.raises(OversizedPaymentHeaderError):
            decode_payment_signature(at_limit)

    def test_header_below_limit_proceeds_to_decode(self):
        # Below limit but invalid Base64 — raises MalformedPaymentError, not oversized
        from hack_pay.errors import MalformedPaymentError
        small_invalid = "not-base64!!!"
        with pytest.raises(MalformedPaymentError):
            decode_payment_signature(small_invalid)