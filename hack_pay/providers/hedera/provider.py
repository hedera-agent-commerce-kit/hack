"""
hack_pay.providers.hedera.provider — HederaPaymentProvider implementation.

Delegates all on-chain work to a public x402 facilitator (Blocky402 by
default).  The resource server never holds a private key or a Hedera SDK.

Startup sequence (called once by HackPay.startup()):
  1. GET /supported  → cache feePayer account ID
  2. Validate that the configured network + scheme=exact is advertised
  3. Log network, receiver_account_id, facilitator_url, feePayer
     (never log private keys — there are none here)

Request sequence (concurrent-safe):
  verify() → settle() orchestrated by PaymentGate
"""

from __future__ import annotations

import logging

from hack_pay.errors import (
    ConfigurationError,
    FacilitatorNetworkNotSupportedError,
)
from hack_pay.providers.base import PaymentProvider, SettleResult, VerifyResult
from hack_pay.providers.hedera.config import HederaProviderConfig
from hack_pay.providers.hedera.facilitator import FacilitatorClient
from hack_pay.x402.types import PaymentPayload, PaymentRequirements

logger = logging.getLogger(__name__)


class HederaPaymentProvider(PaymentProvider):
    """
    PaymentProvider implementation for Hedera using a public x402 facilitator.

    Parameters
    ----------
    config:
        Validated HederaProviderConfig instance.
    """

    def __init__(self, config: HederaProviderConfig) -> None:
        self._config = config
        self._client = FacilitatorClient(
            base_url=config.facilitator_url,
            timeout_seconds=config.facilitator_timeout_seconds,
            max_retries=config.max_retries,
            backoff_seconds=config.retry_backoff_seconds,
        )
        self._fee_payer: str | None = None  # set in initialize()

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """
        Fetch /supported and cache the feePayer account ID.

        Raises
        ------
        FacilitatorNetworkNotSupportedError
            If the facilitator does not advertise hedera scheme=exact for the
            configured network.
        FacilitatorUnavailableError / FacilitatorTimeoutError
            If the facilitator cannot be reached at startup.
        """
        supported = await self._client.get_supported()

        matching = [
            k
            for k in supported.kinds
            if k.network == self._config.network and k.scheme == "exact" and k.fee_payer is not None
        ]
        if not matching:
            raise FacilitatorNetworkNotSupportedError(
                f"Facilitator at {self._config.facilitator_url!r} does not "
                f"advertise scheme=exact for network={self._config.network!r}. "
                f"Available kinds: {[f'{k.scheme}/{k.network}' for k in supported.kinds]}"
            )

        self._fee_payer = matching[0].fee_payer
        logger.info(
            "HederaPaymentProvider initialised",
            extra={
                "network": self._config.network,
                "receiver_account_id": self._config.receiver_account_id,
                "facilitator_url": self._config.facilitator_url,
                "fee_payer": self._fee_payer,
                # private keys: none — server holds no keys
            },
        )

    async def close(self) -> None:
        await self._client.close()

    # ── Payment operations ────────────────────────────────────────────────

    async def build_payment_requirements(self, config: object) -> PaymentRequirements:
        """
        Build PaymentRequirements for the 402 challenge.

        The ``extra.feePayer`` field is populated with the facilitator fee-payer
        account fetched during initialize() — required by the Hedera exact scheme.
        """
        if self._fee_payer is None:
            raise ConfigurationError(
                "HederaPaymentProvider.initialize() was not called. "
                "Ensure HackPay.startup() is awaited before serving requests."
            )
        # Import here to avoid circular dependency at module level
        from hack_pay.core.types import PaymentConfig  # noqa: E402

        cfg: PaymentConfig = config  # type: ignore[assignment]
        return PaymentRequirements.model_validate(
            {
                "scheme": "exact",
                "network": self._config.network,
                "payTo": self._config.receiver_account_id,
                "amount": str(cfg.amount_tinybars),
                "asset": cfg.asset,
                "description": cfg.description,
                "maxTimeoutSeconds": cfg.max_deadline_seconds,
                "extra": {"feePayer": self._fee_payer},
            }
        )

    async def verify(
        self,
        payload: PaymentPayload,
        requirements: PaymentRequirements,
    ) -> VerifyResult:
        resp = await self._client.verify(payload, requirements)
        if not resp.is_valid:
            return VerifyResult.failure(resp.failure_reason)
        return VerifyResult.success()

    async def settle(
        self,
        payload: PaymentPayload,
        requirements: PaymentRequirements,
    ) -> SettleResult:
        resp = await self._client.settle(payload, requirements)
        if not resp.success:
            if resp.error_reason == "settlement_pending" and resp.transaction:
                net = resp.network or ""
                return SettleResult.failure(f"settlement_pending:{resp.transaction}:{net}")
            return SettleResult.failure(resp.error or "Settlement failed")
        if resp.transaction is None:
            return SettleResult.failure("Facilitator returned no transaction ID")
        return SettleResult.success(
            transaction_id=resp.transaction,
            payer=resp.payer,
        )
