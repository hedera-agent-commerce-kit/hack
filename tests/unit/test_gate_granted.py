"""tests/unit/test_gate_granted.py — PaymentGate granted phase."""

import base64
import pytest
from hack_pay.core.types import RequestContext


def _make_sig(payload_bytes: bytes = b"fake-tx") -> str:
    import json
    data = {
        "x402_version": 2, "scheme": "exact",
        "network": "hedera:testnet",
        "payload": base64.b64encode(payload_bytes).decode(),
    }
    return base64.b64encode(json.dumps(data).encode()).decode()


@pytest.mark.asyncio
class TestGateGranted:
    async def test_valid_payment_returns_granted(self, payment_gate, valid_payment_config):
        sig = _make_sig()
        ctx = RequestContext(endpoint="/test", method="GET", payment_signature=sig)
        result = await payment_gate.gate(ctx, valid_payment_config)
        assert result.kind == "granted"

    async def test_receipt_has_transaction_id(self, payment_gate, valid_payment_config):
        sig = _make_sig()
        ctx = RequestContext(endpoint="/test", method="GET", payment_signature=sig)
        result = await payment_gate.gate(ctx, valid_payment_config)
        assert result.receipt.transaction_id == "0.0.12345@1725000000.000000000"

    async def test_receipt_has_correct_network(self, payment_gate, valid_payment_config):
        sig = _make_sig()
        ctx = RequestContext(endpoint="/test", method="GET", payment_signature=sig)
        result = await payment_gate.gate(ctx, valid_payment_config)
        assert result.receipt.network == "hedera:testnet"

    async def test_replay_returns_granted_without_second_settle(
        self, payment_gate, mock_provider, valid_payment_config
    ):
        sig = _make_sig(b"unique-tx-bytes")
        ctx = RequestContext(endpoint="/test", method="GET", payment_signature=sig)
        # First call
        r1 = await payment_gate.gate(ctx, valid_payment_config)
        assert r1.kind == "granted"
        # Replay — same sig
        r2 = await payment_gate.gate(ctx, valid_payment_config)
        assert r2.kind == "granted"
        # settle was called only once
        assert mock_provider.settle.call_count == 1