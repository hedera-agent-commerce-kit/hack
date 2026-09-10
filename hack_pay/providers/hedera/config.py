"""
hack_pay.providers.hedera.config — HederaProviderConfig dataclass.

Validates all values at construction time so misconfiguration is caught
at startup, not during the first payment request.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from hack_pay.errors import ConfigurationError

_HEDERA_ACCOUNT_RE = re.compile(r"^\d+\.\d+\.\d+$")
_HTTPS_URL_RE = re.compile(r"^https://[A-Za-z0-9.\-]+(:\d+)?(/.*)?$")

# Known-good facilitator base URLs (informational — not used for allowlist enforcement,
# but shown in error messages to guide misconfigured users).
BLOCKY402_TESTNET = "https://api.testnet.blocky402.com"
BLOCKY402_MAINNET = "https://api.blocky402.com"
X402_ORG_TESTNET = "https://x402.org/facilitator"


def _validate_account_id(account_id: str) -> str:
    if not _HEDERA_ACCOUNT_RE.match(account_id):
        raise ConfigurationError(
            f"receiver_account_id must be in Hedera shard.realm.num format "
            f"(e.g. '0.0.12345'), got: {account_id!r}"
        )
    return account_id


def _validate_facilitator_url(url: str) -> str:
    """
    Require HTTPS and a hostname that contains no private-IP literals.

    This is a lightweight SSRF guard.  The facilitator URL comes from
    server-side configuration only — never from request input.
    """
    if not _HTTPS_URL_RE.match(url):
        raise ConfigurationError(
            f"facilitator_url must be an HTTPS URL (e.g. '{BLOCKY402_TESTNET}'), got: {url!r}"
        )
    # Block obvious private-IP targets
    for private in ("localhost", "127.", "10.", "192.168.", "172.16.", "::1"):
        if private in url:
            raise ConfigurationError(
                f"facilitator_url must not point to a private/loopback address, got: {url!r}"
            )
    return url


@dataclass(frozen=True)
class HederaProviderConfig:
    """
    Configuration for HederaPaymentProvider.

    Parameters
    ----------
    network:
        CAIP-2 network identifier. ``"hedera:testnet"`` or ``"hedera:mainnet"``.
    receiver_account_id:
        Hedera account that receives HBAR payments (your wallet).
        Format: ``"0.0.XXXXX"``.
    facilitator_url:
        Base URL of the x402 facilitator. Defaults to Blocky402 testnet.
        Switch to ``BLOCKY402_MAINNET`` for production.
    facilitator_timeout_seconds:
        HTTP timeout for /verify and /settle calls. Default: 10 s.
    max_retries:
        Number of retry attempts on transient facilitator errors. Default: 2.
    retry_backoff_seconds:
        Base backoff between retries (exponential). Default: 0.5 s.
    """

    network: str
    receiver_account_id: str
    facilitator_url: str = BLOCKY402_TESTNET
    facilitator_timeout_seconds: int = 10
    max_retries: int = 2
    retry_backoff_seconds: float = 0.5

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "receiver_account_id",
            _validate_account_id(self.receiver_account_id),
        )
        object.__setattr__(
            self,
            "facilitator_url",
            _validate_facilitator_url(self.facilitator_url),
        )
        if self.network not in ("hedera:testnet", "hedera:mainnet"):
            raise ConfigurationError(
                f"network must be 'hedera:testnet' or 'hedera:mainnet', got: {self.network!r}"
            )
        if self.facilitator_timeout_seconds < 1:
            raise ConfigurationError("facilitator_timeout_seconds must be >= 1")
        if self.max_retries < 0:
            raise ConfigurationError("max_retries must be >= 0")
