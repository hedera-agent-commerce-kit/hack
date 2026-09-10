"""tests/integration/test_facilitator_timeout.py — Facilitator timeout handling."""

import base64
import json
from unittest.mock import AsyncMock

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from hack_pay import paid
from hack_pay.core.gate import PaymentGate
from hack_pay.errors import FacilitatorTimeoutError
from hack_pay.idempotency.memory import InMemoryIdempotencyStore
from hack_pay.receipts.noop import NoopReceiptPublisher


def _make_app_with_provider(provider):
    app = FastAPI()
    gate = PaymentGate(
        provider=provider,
        idempotency_store=InMemoryIdempotencyStore(),
        receipt_publisher=NoopReceiptPublisher(),
    )
    app.state.hack_pay_gate = gate

    @app.get("/endpoint")
    @paid("0.5 HBAR")
    async def endpoint(request: Request):
        return {"ok": True}

    return TestClient(app, raise_server_exceptions=False)


class TestFacilitatorTimeout:
    def test_verify_timeout_returns_504(self):
        from hack_pay.x402.types import PaymentRequirements

        provider = AsyncMock()
        provider.build_payment_requirements = AsyncMock(
            return_value=PaymentRequirements(
                scheme="exact",
                network="hedera:testnet",
                pay_to="0.0.12345",
                amount="50000000",
                extra={"feePayer": "0.0.7162784"},
            )
        )
        provider.verify = AsyncMock(side_effect=FacilitatorTimeoutError("timed out"))
        cfg = AsyncMock()
        cfg.facilitator_url = "https://api.testnet.blocky402.com"
        provider._config = cfg
        client = _make_app_with_provider(provider)
        data = {
            "x402_version": 2,
            "scheme": "exact",
            "network": "hedera:testnet",
            "payload": base64.b64encode(b"tx").decode(),
        }
        sig = base64.b64encode(json.dumps(data).encode()).decode()
        resp = client.get("/endpoint", headers={"PAYMENT-SIGNATURE": sig})
        assert resp.status_code == 504

    def test_settle_timeout_returns_504(self):
        from hack_pay.providers.base import VerifyResult
        from hack_pay.x402.types import PaymentRequirements

        provider = AsyncMock()
        provider.build_payment_requirements = AsyncMock(
            return_value=PaymentRequirements(
                scheme="exact",
                network="hedera:testnet",
                pay_to="0.0.12345",
                amount="50000000",
                extra={"feePayer": "0.0.7162784"},
            )
        )
        provider.verify = AsyncMock(return_value=VerifyResult.success())
        provider.settle = AsyncMock(side_effect=FacilitatorTimeoutError("settle timed out"))
        cfg = AsyncMock()
        cfg.facilitator_url = "https://api.testnet.blocky402.com"
        provider._config = cfg
        client = _make_app_with_provider(provider)
        data = {
            "x402_version": 2,
            "scheme": "exact",
            "network": "hedera:testnet",
            "payload": base64.b64encode(b"tx-settle").decode(),
        }
        sig = base64.b64encode(json.dumps(data).encode()).decode()
        resp = client.get("/endpoint", headers={"PAYMENT-SIGNATURE": sig})
        assert resp.status_code == 504
