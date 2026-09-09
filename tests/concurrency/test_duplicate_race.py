"""tests/concurrency/test_duplicate_race.py — Concurrent identical proofs settle exactly once."""

import asyncio, base64, json, pytest
from unittest.mock import AsyncMock
from hack_pay.core.gate import PaymentGate
from hack_pay.core.types import PaymentConfig, RequestContext
from hack_pay.idempotency.memory import InMemoryIdempotencyStore
from hack_pay.providers.base import SettleResult, VerifyResult
from hack_pay.receipts.noop import NoopReceiptPublisher
from hack_pay.x402.types import PaymentRequirements


def _make_provider():
    provider = AsyncMock()
    req = PaymentRequirements(scheme="exact", network="hedera:testnet",
                               pay_to="0.0.12345", amount="50000000",
                               extra={"feePayer": "0.0.7162784"})
    provider.build_payment_requirements = AsyncMock(return_value=req)
    provider.verify = AsyncMock(return_value=VerifyResult.success())
    provider.settle = AsyncMock(return_value=SettleResult.success("tx-race"))
    cfg = AsyncMock(); cfg.facilitator_url = "https://facilitator"
    provider._config = cfg
    return provider


def _sig(payload_bytes: bytes) -> str:
    data = {"x402_version": 2, "scheme": "exact",
            "network": "hedera:testnet",
            "payload": base64.b64encode(payload_bytes).decode()}
    return base64.b64encode(json.dumps(data).encode()).decode()


@pytest.mark.asyncio
class TestConcurrentDuplicates:
    async def test_100_concurrent_identical_proofs_settle_exactly_once(self):
        provider = _make_provider()
        gate = PaymentGate(
            provider=provider,
            idempotency_store=InMemoryIdempotencyStore(),
            receipt_publisher=NoopReceiptPublisher(),
        )
        config = PaymentConfig(amount_tinybars=50_000_000, network="hedera:testnet")
        sig = _sig(b"concurrent-race-proof")
        ctx = RequestContext(endpoint="/test", method="GET", payment_signature=sig)

        results = await asyncio.gather(*[gate.gate(ctx, config) for _ in range(100)])

        # All requests get granted
        assert all(r.kind == "granted" for r in results)
        # Settle called exactly once despite 100 concurrent requests
        assert provider.settle.call_count == 1
        # All receipts have the same transaction_id
        tx_ids = {r.receipt.transaction_id for r in results}
        assert len(tx_ids) == 1

    async def test_different_proofs_all_settle_independently(self):
        provider = _make_provider()
        gate = PaymentGate(
            provider=provider,
            idempotency_store=InMemoryIdempotencyStore(),
            receipt_publisher=NoopReceiptPublisher(),
        )
        config = PaymentConfig(amount_tinybars=50_000_000, network="hedera:testnet")

        async def pay(i: int):
            sig = _sig(f"unique-proof-{i}".encode())
            ctx = RequestContext(endpoint="/test", method="GET", payment_signature=sig)
            return await gate.gate(ctx, config)

        results = await asyncio.gather(*[pay(i) for i in range(10)])
        assert all(r.kind == "granted" for r in results)
        assert provider.settle.call_count == 10