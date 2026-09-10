"""tests/unit/test_config_validation.py — HederaProviderConfig validation."""

import pytest

from hack_pay.errors import ConfigurationError
from hack_pay.providers.hedera.config import HederaProviderConfig


class TestHederaProviderConfig:
    def test_valid_testnet_config(self):
        cfg = HederaProviderConfig(network="hedera:testnet", receiver_account_id="0.0.12345")
        assert cfg.network == "hedera:testnet"
        assert cfg.receiver_account_id == "0.0.12345"

    def test_valid_mainnet_config(self):
        cfg = HederaProviderConfig(
            network="hedera:mainnet",
            receiver_account_id="0.0.99999",
            facilitator_url="https://api.blocky402.com",
        )
        assert cfg.network == "hedera:mainnet"

    def test_invalid_network_raises(self):
        with pytest.raises(ConfigurationError, match="network"):
            HederaProviderConfig(network="eip155:1", receiver_account_id="0.0.12345")

    def test_invalid_account_format_raises(self):
        with pytest.raises(ConfigurationError, match="receiver_account_id"):
            HederaProviderConfig(network="hedera:testnet", receiver_account_id="not-an-account")

    def test_http_facilitator_url_raises(self):
        with pytest.raises(ConfigurationError, match="HTTPS"):
            HederaProviderConfig(
                network="hedera:testnet",
                receiver_account_id="0.0.12345",
                facilitator_url="http://api.testnet.blocky402.com",
            )

    def test_localhost_facilitator_url_raises(self):
        with pytest.raises(ConfigurationError, match="private"):
            HederaProviderConfig(
                network="hedera:testnet",
                receiver_account_id="0.0.12345",
                facilitator_url="https://localhost:4020",
            )

    def test_private_ip_facilitator_url_raises(self):
        with pytest.raises(ConfigurationError, match="private"):
            HederaProviderConfig(
                network="hedera:testnet",
                receiver_account_id="0.0.12345",
                facilitator_url="https://192.168.1.1/facilitator",
            )

    def test_negative_timeout_raises(self):
        with pytest.raises(ConfigurationError):
            HederaProviderConfig(
                network="hedera:testnet",
                receiver_account_id="0.0.12345",
                facilitator_timeout_seconds=0,
            )

    def test_default_facilitator_is_blocky402_testnet(self):
        cfg = HederaProviderConfig(network="hedera:testnet", receiver_account_id="0.0.12345")
        assert "blocky402" in cfg.facilitator_url

    def test_mainnet_default_facilitator_is_blocky402_mainnet(self):
        cfg = HederaProviderConfig(network="hedera:mainnet", receiver_account_id="0.0.99999")
        assert "blocky402.com" in cfg.facilitator_url
        assert "testnet" not in cfg.facilitator_url

    def test_testnet_default_facilitator_is_blocky402_testnet(self):
        cfg = HederaProviderConfig(network="hedera:testnet", receiver_account_id="0.0.12345")
        assert "testnet.blocky402.com" in cfg.facilitator_url
