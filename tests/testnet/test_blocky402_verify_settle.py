"""
tests/testnet/test_blocky402_verify_settle.py — Live Blocky402 facilitator tests.

Opt-in: requires HACK_PAY_TESTNET_* env vars. Never runs in CI.
Tests GET /supported and POST /verify against the real Blocky402 testnet endpoint.
No real payment is made in these tests (verify-only, no settle).
"""

import pytest
from hack_pay.providers.hedera.facilitator import FacilitatorClient
from hack_pay.providers.hedera.config import BLOCKY402_TESTNET


@pytest.mark.testnet
@pytest.mark.asyncio
class TestBlocky402Live:
    async def test_get_supported_returns_hedera_testnet(self, testnet_env):
        client = FacilitatorClient(base_url=BLOCKY402_TESTNET, timeout_seconds=15)
        try:
            supported = await client.get_supported()
            hedera_kinds = [
                k for k in supported.kinds
                if k.network == "hedera:testnet" and k.scheme == "exact"
            ]
            assert len(hedera_kinds) >= 1, (
                "Blocky402 testnet did not advertise hedera:testnet/exact. "
                f"Got: {supported.kinds}"
            )
            assert hedera_kinds[0].fee_payer is not None
        finally:
            await client.close()

    async def test_health_check_passes(self, testnet_env):
        client = FacilitatorClient(base_url=BLOCKY402_TESTNET, timeout_seconds=10)
        try:
            result = await client.health_check()
            assert result is True
        finally:
            await client.close()