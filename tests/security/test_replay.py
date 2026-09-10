"""tests/security/test_replay.py — Replay attack: same payment proof must not double-settle."""

import base64
import json
from unittest.mock import AsyncMock

import pytest

from hack_pay.core.gate import PaymentGate
from hack_pay.core.types import PaymentConfig, RequestContext
from hack_pay.idempotency.memory import InMemoryIdempotencyStore
from hack_pay.providers.base import SettleResult, VerifyResult
from hack_pay.receipts.noop import NoopReceiptPublisher
from hack_pay.x402.types import PaymentRequirements


def _make_gate_with_mock_provider(tx_id: str = "tx-1"):
    provider = AsyncMock()
    req = PaymentRequirements(
        scheme="exact",
        network="hedera:testnet",
        pay_to="0.0.12345",
        amount="50000000",
        extra={"feePayer": "0.0.7162784"},
    )
    provider.build_payment_requirements = AsyncMock(return_value=req)
    provider.verify = AsyncMock(return_value=VerifyResult.success())
    provider.settle = AsyncMock(return_value=SettleResult.success(tx_id))
    cfg = AsyncMock()
    cfg.facilitator_url = "https://facilitator"
    provider._config = cfg
    gate = PaymentGate(
        provider=provider,
        idempotency_store=InMemoryIdempotencyStore(),
        receipt_publisher=NoopReceiptPublisher(),
    )
    return gate, provider


def _sig(payload_bytes: bytes) -> str:
    data = {
        "x402_version": 2,
        "scheme": "exact",
        "network": "hedera:testnet",
        "payload": base64.b64encode(payload_bytes).decode(),
    }
    return base64.b64encode(json.dumps(data).encode()).decode()


config = PaymentConfig(amount_tinybars=50_000_000, network="hedera:testnet")


@pytest.mark.asyncio
class TestReplayAttack:
    async def test_same_proof_replayed_10_times_settles_once(self):
        gate, provider = _make_gate_with_mock_provider()
        sig = _sig(b"replay-proof")
        ctx = RequestContext(endpoint="/test", method="GET", payment_signature=sig)
        for _ in range(10):
            result = await gate.gate(ctx, config)
            assert result.kind == "granted"
        assert provider.settle.call_count == 1

    async def test_different_proofs_settle_independently(self):
        gate, provider = _make_gate_with_mock_provider()
        for i in range(3):
            sig = _sig(f"unique-proof-{i}".encode())
            ctx = RequestContext(endpoint="/test", method="GET", payment_signature=sig)
            result = await gate.gate(ctx, config)
            assert result.kind == "granted"
        assert provider.settle.call_count == 3
