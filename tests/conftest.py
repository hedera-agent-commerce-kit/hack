"""
tests/conftest.py — Shared pytest fixtures for all test suites.

These fixtures provide:
- A valid fake PaymentPayload (deterministic, no real Hedera tx)
- A mock FacilitatorClient that returns success responses
- A configured HederaPaymentProvider backed by the mock client
- A PaymentGate wired with in-memory idempotency and noop receipt publisher
- A FastAPI TestClient with the gate attached to app.state
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from hack_pay.core.gate import PaymentGate
from hack_pay.core.types import PaymentConfig
from hack_pay.idempotency.memory import InMemoryIdempotencyStore
from hack_pay.observability.logging import LoggingPaymentEventHook
from hack_pay.providers.base import SettleResult, VerifyResult
from hack_pay.providers.hedera.facilitator import FacilitatorClient
from hack_pay.providers.hedera.provider import HederaPaymentProvider
from hack_pay.providers.hedera.types import (
    FacilitatorSupportedResponse,
    FacilitatorVerifyResponse,
    SupportedKind,
)
from hack_pay.receipts.noop import NoopReceiptPublisher
from hack_pay.receipts.types import PaymentReceipt
from hack_pay.x402.types import PaymentPayload, PaymentRequirements, SettlementResponse

# ── Constants ─────────────────────────────────────────────────────────────────

TESTNET_NETWORK = "hedera:testnet"
RECEIVER_ACCOUNT = "0.0.12345"
FEE_PAYER_ACCOUNT = "0.0.7162784"  # Blocky402 testnet fee payer
FAKE_TX_ID = "0.0.12345@1725000000.000000000"
FAKE_TX_BYTES = b"fake-hedera-transfer-tx-bytes-deterministic"
FACILITATOR_URL = "https://api.testnet.blocky402.com"
AMOUNT_TINYBARS = 50_000_000  # 0.5 HBAR


# ── x402 wire fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def fake_tx_b64() -> str:
    """Deterministic Base64-encoded fake transaction bytes."""
    return base64.b64encode(FAKE_TX_BYTES).decode()


@pytest.fixture
def valid_payload(fake_tx_b64: str) -> PaymentPayload:
    """A valid x402 v2 PaymentPayload (no real Hedera transaction)."""
    return PaymentPayload(
        x402_version=2,
        scheme="exact",
        network=TESTNET_NETWORK,
        payload=fake_tx_b64,
    )


@pytest.fixture
def valid_requirements() -> PaymentRequirements:
    """PaymentRequirements matching the default test configuration."""
    return PaymentRequirements(
        scheme="exact",
        network=TESTNET_NETWORK,
        pay_to=RECEIVER_ACCOUNT,
        amount=str(AMOUNT_TINYBARS),
        asset="0.0.0",
        max_deadline_seconds=300,
        extra={"feePayer": FEE_PAYER_ACCOUNT},
    )


@pytest.fixture
def valid_payment_config() -> PaymentConfig:
    return PaymentConfig(
        amount_tinybars=AMOUNT_TINYBARS,
        network=TESTNET_NETWORK,
    )


@pytest.fixture
def valid_receipt() -> PaymentReceipt:
    return PaymentReceipt(
        transaction_id=FAKE_TX_ID,
        payer_account_id="0.0.99999",
        receiver_account_id=RECEIVER_ACCOUNT,
        amount_tinybars=AMOUNT_TINYBARS,
        asset="0.0.0",
        network=TESTNET_NETWORK,
        settled_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        facilitator_url=FACILITATOR_URL,
    )


# ── Mock facilitator fixtures ─────────────────────────────────────────────────


@pytest.fixture
def mock_facilitator_client() -> AsyncMock:
    """FacilitatorClient mock that returns success responses."""
    client = AsyncMock(spec=FacilitatorClient)
    client.get_supported.return_value = FacilitatorSupportedResponse(
        kinds=[SupportedKind(scheme="exact", network=TESTNET_NETWORK, feePayer=FEE_PAYER_ACCOUNT)]
    )
    client.verify.return_value = FacilitatorVerifyResponse(isValid=True)
    client.settle.return_value = SettlementResponse(
        success=True,
        transaction=FAKE_TX_ID,
        network=TESTNET_NETWORK,
        payer="0.0.99999",
    )
    client.close = AsyncMock()
    client.health_check = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_provider(
    mock_facilitator_client: AsyncMock, valid_requirements: PaymentRequirements
) -> AsyncMock:  # noqa: E501
    """HederaPaymentProvider mock wired to return success results."""
    provider = AsyncMock(spec=HederaPaymentProvider)
    provider.build_payment_requirements = AsyncMock(return_value=valid_requirements)
    provider.verify = AsyncMock(return_value=VerifyResult.success())
    provider.settle = AsyncMock(
        return_value=SettleResult.success(transaction_id=FAKE_TX_ID, payer="0.0.99999")
    )
    provider.initialize = AsyncMock()
    provider.close = AsyncMock()
    # Expose _config for gate.py receipt building
    cfg = MagicMock()
    cfg.facilitator_url = FACILITATOR_URL
    provider._config = cfg
    return provider


# ── Gate and store fixtures ───────────────────────────────────────────────────


@pytest.fixture
def idempotency_store() -> InMemoryIdempotencyStore:
    return InMemoryIdempotencyStore()


@pytest.fixture
def payment_gate(
    mock_provider: AsyncMock, idempotency_store: InMemoryIdempotencyStore
) -> PaymentGate:  # noqa: E501
    return PaymentGate(
        provider=mock_provider,
        idempotency_store=idempotency_store,
        receipt_publisher=NoopReceiptPublisher(),
        event_hooks=[LoggingPaymentEventHook()],
    )


# ── FastAPI TestClient fixtures ───────────────────────────────────────────────


@pytest.fixture
def test_app(payment_gate: PaymentGate) -> FastAPI:
    """Minimal FastAPI app with gate attached to app.state."""
    from hack_pay import paid

    app = FastAPI()
    app.state.hack_pay_gate = payment_gate

    @app.get("/paid-endpoint")
    @paid("0.5 HBAR")
    async def paid_endpoint(request: Request):
        return {"data": "secret content"}

    @app.get("/free-endpoint")
    async def free_endpoint():
        return {"data": "free content"}

    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    return TestClient(test_app, raise_server_exceptions=False)
