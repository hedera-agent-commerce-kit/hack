"""tests/unit/test_gate_challenge.py — PaymentGate challenge phase."""

import pytest

from hack_pay.core.types import RequestContext


@pytest.mark.asyncio
class TestGateChallenge:
    async def test_no_signature_returns_challenge(self, payment_gate, valid_payment_config):
        ctx = RequestContext(endpoint="/test", method="GET", payment_signature=None)
        result = await payment_gate.gate(ctx, valid_payment_config)
        assert result.kind == "challenge"

    async def test_challenge_contains_requirements(self, payment_gate, valid_payment_config):
        ctx = RequestContext(endpoint="/test", method="GET", payment_signature=None)
        result = await payment_gate.gate(ctx, valid_payment_config)
        assert result.requirements.scheme == "exact"
        assert result.requirements.network == "hedera:testnet"
        assert result.requirements.pay_to == "0.0.12345"
        assert result.requirements.amount == "50000000"

    async def test_challenge_has_fee_payer_in_extra(self, payment_gate, valid_payment_config):
        ctx = RequestContext(endpoint="/test", method="GET", payment_signature=None)
        result = await payment_gate.gate(ctx, valid_payment_config)
        assert "feePayer" in result.requirements.extra
