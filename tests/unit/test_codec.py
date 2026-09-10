"""tests/unit/test_codec.py — x402 header codec encode/decode."""

import base64
import json

import pytest

from hack_pay.errors import (
    MalformedPaymentError,
    OversizedPaymentHeaderError,
    UnsupportedProtocolVersionError,
)
from hack_pay.x402.codec import (
    decode_payment_signature,
    encode_payment_required,
    encode_payment_response,
    extract_payment_signature_header,
)
from hack_pay.x402.types import PaymentPayload, PaymentRequirements, SettlementResponse


@pytest.fixture
def requirements():
    return PaymentRequirements(
        scheme="exact",
        network="hedera:testnet",
        pay_to="0.0.12345",
        amount="50000000",
    )


@pytest.fixture
def payload():
    return PaymentPayload(
        x402_version=2,
        scheme="exact",
        network="hedera:testnet",
        payload=base64.b64encode(b"fake-tx").decode(),
    )


class TestEncodePaymentRequired:
    def test_round_trips_to_valid_base64_json(self, requirements):
        encoded = encode_payment_required(requirements)
        decoded = json.loads(base64.b64decode(encoded))
        assert decoded["scheme"] == "exact"
        assert decoded["network"] == "hedera:testnet"
        assert decoded["payTo"] == "0.0.12345"
        assert decoded["amount"] == "50000000"

    def test_is_ascii_safe(self, requirements):
        encoded = encode_payment_required(requirements)
        encoded.encode("ascii")  # must not raise


class TestDecodePaymentSignature:
    def test_decodes_valid_payload(self, payload):
        encoded = base64.b64encode(payload.model_dump_json().encode()).decode()
        result = decode_payment_signature(encoded)
        assert result.x402_version == 2
        assert result.scheme == "exact"
        assert result.network == "hedera:testnet"

    def test_rejects_oversized_header(self):
        oversized = "A" * 70_000
        with pytest.raises(OversizedPaymentHeaderError):
            decode_payment_signature(oversized)

    def test_rejects_invalid_base64(self):
        with pytest.raises(MalformedPaymentError):
            decode_payment_signature("not-valid-base64!!!")

    def test_rejects_non_json(self):
        encoded = base64.b64encode(b"not json at all").decode()
        with pytest.raises(MalformedPaymentError):
            decode_payment_signature(encoded)

    def test_rejects_v1_version(self):
        data = {"x402Version": 1, "scheme": "exact", "network": "hedera:testnet", "payload": "abc"}
        encoded = base64.b64encode(json.dumps(data).encode()).decode()
        with pytest.raises(UnsupportedProtocolVersionError):
            decode_payment_signature(encoded)

    def test_rejects_missing_fields(self):
        data = {"x402_version": 2}  # missing scheme, network, payload
        encoded = base64.b64encode(json.dumps(data).encode()).decode()
        with pytest.raises(MalformedPaymentError):
            decode_payment_signature(encoded)


class TestExtractPaymentSignatureHeader:
    def test_returns_v2_header(self):
        result = extract_payment_signature_header({"payment-signature": "abc"})
        assert result == "abc"

    def test_case_insensitive(self):
        result = extract_payment_signature_header({"PAYMENT-SIGNATURE": "abc"})
        assert result == "abc"

    def test_returns_none_when_absent(self):
        result = extract_payment_signature_header({"content-type": "application/json"})
        assert result is None

    def test_raises_on_v1_header(self):
        with pytest.raises(UnsupportedProtocolVersionError):
            extract_payment_signature_header({"x-payment": "old-payload"})


class TestEncodePaymentResponse:
    def test_round_trips(self):
        settlement = SettlementResponse(
            success=True, transaction="0.0.1@100.000", network="hedera:testnet"
        )
        encoded = encode_payment_response(settlement)
        decoded = json.loads(base64.b64decode(encoded))
        assert decoded["success"] is True
        assert decoded["transaction"] == "0.0.1@100.000"
