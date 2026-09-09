"""tests/security/test_ssrf.py — SSRF protection via facilitator URL validation."""

import pytest
from hack_pay.errors import ConfigurationError
from hack_pay.providers.hedera.config import HederaProviderConfig


class TestSSRFProtection:
    def test_http_url_rejected(self):
        with pytest.raises(ConfigurationError, match="HTTPS"):
            HederaProviderConfig(
                network="hedera:testnet", receiver_account_id="0.0.12345",
                facilitator_url="http://api.testnet.blocky402.com",
            )

    def test_localhost_rejected(self):
        with pytest.raises(ConfigurationError, match="private"):
            HederaProviderConfig(
                network="hedera:testnet", receiver_account_id="0.0.12345",
                facilitator_url="https://localhost/facilitator",
            )

    def test_127_0_0_1_rejected(self):
        with pytest.raises(ConfigurationError, match="private"):
            HederaProviderConfig(
                network="hedera:testnet", receiver_account_id="0.0.12345",
                facilitator_url="https://127.0.0.1/facilitator",
            )

    def test_private_10_subnet_rejected(self):
        with pytest.raises(ConfigurationError, match="private"):
            HederaProviderConfig(
                network="hedera:testnet", receiver_account_id="0.0.12345",
                facilitator_url="https://10.0.0.1/facilitator",
            )

    def test_valid_public_url_accepted(self):
        cfg = HederaProviderConfig(
            network="hedera:testnet", receiver_account_id="0.0.12345",
            facilitator_url="https://api.testnet.blocky402.com",
        )
        assert cfg.facilitator_url == "https://api.testnet.blocky402.com"