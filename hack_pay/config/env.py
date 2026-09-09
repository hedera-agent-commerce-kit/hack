"""
hack_pay.config.env — Load HederaProviderConfig from environment variables.

Environment variables
---------------------
HACK_PAY_RECEIVER_ACCOUNT_ID  (required)
    Hedera account that receives HBAR payments. Format: 0.0.XXXXX.

HACK_PAY_HEDERA_NETWORK  (optional, default: hedera:testnet)
    CAIP-2 network identifier. "hedera:testnet" or "hedera:mainnet".

HACK_PAY_FACILITATOR_URL  (optional, default: Blocky402 testnet)
    Base URL of the x402 facilitator.

See .env.example in the repository root for all available variables.
"""

from __future__ import annotations

import logging
import os

from hack_pay.errors import ConfigurationError
from hack_pay.providers.hedera.config import (
    BLOCKY402_TESTNET,
    HederaProviderConfig,
)

logger = logging.getLogger(__name__)


def load_hedera_config_from_env() -> HederaProviderConfig:
    """
    Build a HederaProviderConfig from environment variables.

    Raises
    ------
    ConfigurationError
        If HACK_PAY_RECEIVER_ACCOUNT_ID is not set.
    """
    account_id = os.environ.get("HACK_PAY_RECEIVER_ACCOUNT_ID", "").strip()
    if not account_id:
        raise ConfigurationError(
            "HACK_PAY_RECEIVER_ACCOUNT_ID is required but not set. "
            "Set it to your Hedera receiver account (e.g. 0.0.12345). "
            "See .env.example for all configuration options."
        )

    network = os.environ.get("HACK_PAY_HEDERA_NETWORK", "hedera:testnet").strip()
    facilitator_url = os.environ.get(
        "HACK_PAY_FACILITATOR_URL", BLOCKY402_TESTNET
    ).strip()

    # Log which vars are configured — never log values of secrets
    logger.info(
        "Loading Hedera config from environment",
        extra={
            "HACK_PAY_RECEIVER_ACCOUNT_ID": "set",
            "HACK_PAY_HEDERA_NETWORK": network,
            "HACK_PAY_FACILITATOR_URL": facilitator_url,
        },
    )

    return HederaProviderConfig(
        network=network,
        receiver_account_id=account_id,
        facilitator_url=facilitator_url,
    )