"""tests/protocol/test_payment_required_header.py — PAYMENT-REQUIRED header conformance."""

import base64
import json

import pytest

from hack_pay.x402.codec import encode_payment_required
from hack_pay.x402.types import PaymentRequirements


class TestPaymentRequiredHeader:
    def test_scheme_is_exact(self):
        req = PaymentRequirements(
            scheme="exact", network="hedera:testnet", pay_to="0.0.12345", amount="50000000"
        )
        decoded = json.loads(base64.b64decode(encode_payment_required(req)))
        assert decoded["scheme"] == "exact"

    def test_amount_is_string(self):
        req = PaymentRequirements(
            scheme="exact", network="hedera:testnet", pay_to="0.0.12345", amount="50000000"
        )
        decoded = json.loads(base64.b64decode(encode_payment_required(req)))
        assert isinstance(decoded["amount"], str)

    def test_network_is_caip2(self):
        req = PaymentRequirements(
            scheme="exact", network="hedera:testnet", pay_to="0.0.12345", amount="50000000"
        )
        assert req.network.startswith("hedera:")

    def test_negative_amount_rejected(self):
        with pytest.raises(ValueError):
            PaymentRequirements(
                scheme="exact", network="hedera:testnet", pay_to="0.0.12345", amount="-1"
            )

    def test_zero_amount_rejected(self):
        with pytest.raises(ValueError):
            PaymentRequirements(
                scheme="exact", network="hedera:testnet", pay_to="0.0.12345", amount="0"
            )

    def test_fee_payer_in_extra(self):
        req = PaymentRequirements(
            scheme="exact",
            network="hedera:testnet",
            pay_to="0.0.12345",
            amount="50000000",
            extra={"feePayer": "0.0.7162784"},
        )
        decoded = json.loads(base64.b64decode(encode_payment_required(req)))
        assert decoded["extra"]["feePayer"] == "0.0.7162784"
