"""tests/unit/test_gate_errors.py — PaymentGate error handling."""

import base64
import json
from unittest.mock import AsyncMock

import pytest

from hack_pay.core.types import RequestContext
from hack_pay.providers.base import SettleResult, VerifyResult


def _sig(payload_bytes: bytes = b"tx") -> str:
    data = {
        "x402_version": 2,
        "scheme": "exact",
        "network": "hedera:testnet",
        "payload": base64.b64encode(payload_bytes).decode(),
    }
    return base64.b64encode(json.dumps(data).encode()).decode()


@pytest.mark.asyncio
class TestGateErrors:
    async def test_verify_failure_returns_error(
        self, payment_gate, mock_provider, valid_payment_config
    ):
        mock_provider.verify = AsyncMock(return_value=VerifyResult.failure("bad sig"))
        ctx = RequestContext(endpoint="/test", method="GET", payment_signature=_sig())
        result = await payment_gate.gate(ctx, valid_payment_config)
        assert result.kind == "error"

    async def test_settle_failure_returns_error(
        self, payment_gate, mock_provider, valid_payment_config
    ):
        mock_provider.settle = AsyncMock(return_value=SettleResult.failure("network down"))
        ctx = RequestContext(endpoint="/test", method="GET", payment_signature=_sig(b"tx2"))
        result = await payment_gate.gate(ctx, valid_payment_config)
        assert result.kind == "error"

    async def test_settled_receiver_mismatch_is_not_cached(
        self, payment_gate, mock_provider, valid_payment_config
    ):
        mock_provider.settle = AsyncMock(
            return_value=SettleResult.success("tx-wrong-recipient", receiver="0.0.99999")
        )
        ctx = RequestContext(endpoint="/test", method="GET", payment_signature=_sig(b"tx-wrong"))

        first = await payment_gate.gate(ctx, valid_payment_config)
        second = await payment_gate.gate(ctx, valid_payment_config)

        assert first.kind == "error"
        assert second.kind == "error"
        assert mock_provider.settle.call_count == 2

    async def test_malformed_signature_returns_error(self, payment_gate, valid_payment_config):
        """Malformed signatures remain safely wrapped."""
        ctx = RequestContext(
            endpoint="/test", method="GET", payment_signature="not-valid-base64!!!"
        )
        result = await payment_gate.gate(ctx, valid_payment_config)
        assert result.kind == "error"

    async def test_wrong_network_returns_error(self, payment_gate, valid_payment_config):
        data = {
            "x402_version": 2,
            "scheme": "exact",
            "network": "hedera:mainnet",  # wrong network
            "payload": base64.b64encode(b"tx3").decode(),
        }
        sig = base64.b64encode(json.dumps(data).encode()).decode()
        ctx = RequestContext(endpoint="/test", method="GET", payment_signature=sig)
        result = await payment_gate.gate(ctx, valid_payment_config)
        assert result.kind == "error"

    async def test_error_result_never_raises(self, payment_gate, valid_payment_config):
        # Verify that even a catastrophic provider crash returns ErrorResult
        from hack_pay.errors import FacilitatorError

        mock_provider = AsyncMock()
        mock_provider.build_payment_requirements = AsyncMock(side_effect=FacilitatorError("boom"))
        from hack_pay.core.gate import PaymentGate
        from hack_pay.idempotency.memory import InMemoryIdempotencyStore
        from hack_pay.receipts.noop import NoopReceiptPublisher

        gate = PaymentGate(
            provider=mock_provider,
            idempotency_store=InMemoryIdempotencyStore(),
            receipt_publisher=NoopReceiptPublisher(),
        )
        ctx = RequestContext(endpoint="/test", method="GET", payment_signature=None)
        result = await gate.gate(ctx, valid_payment_config)
        # Should return error or challenge — never raise
        assert result.kind in ("error", "challenge")
