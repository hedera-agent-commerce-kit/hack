"""
hack_pay.adapters.fastapi.app â€” HackPay application wrapper.

HackPay wires together the provider, gate, idempotency store, receipt
publisher, and event hooks, then registers them with the FastAPI app via
the lifespan context manager pattern.

Usage
-----
    from contextlib import asynccontextmanager
    from fastapi import FastAPI
    from hack_pay import HackPay, HackPayConfig
    from hack_pay.providers.hedera import HederaPaymentProvider, HederaProviderConfig

    provider = HederaPaymentProvider(HederaProviderConfig(
        network="hedera:testnet",
        receiver_account_id="0.0.12345",
    ))

    hack = HackPay(HackPayConfig(provider=provider))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await hack.startup(app)
        yield
        await hack.shutdown()

    app = FastAPI(lifespan=lifespan)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from hack_pay.core.gate import PaymentGate
from hack_pay.core.types import PaymentConfig
from hack_pay.idempotency.base import IdempotencyStore
from hack_pay.idempotency.memory import InMemoryIdempotencyStore
from hack_pay.observability.base import PaymentEventHook
from hack_pay.observability.logging import LoggingPaymentEventHook
from hack_pay.providers.base import PaymentProvider
from hack_pay.receipts.base import ReceiptPublisher
from hack_pay.receipts.noop import NoopReceiptPublisher

logger = logging.getLogger(__name__)


@dataclass
class HackPayConfig:
    """
    Top-level HACK.Pay configuration.

    Parameters
    ----------
    provider:
        Initialised PaymentProvider (e.g. HederaPaymentProvider).
    idempotency_store:
        Idempotency store. Defaults to InMemoryIdempotencyStore.
        Replace with a Redis-backed implementation for multi-process production.
    receipt_publisher:
        Receipt publisher. Defaults to NoopReceiptPublisher.
    event_hooks:
        List of PaymentEventHook implementations. LoggingPaymentEventHook is
        added automatically if the list is empty.
    default_payment_config:
        Optional default PaymentConfig applied when @paid is used without args.
    """

    provider: PaymentProvider
    idempotency_store: IdempotencyStore = field(
        default_factory=InMemoryIdempotencyStore
    )
    receipt_publisher: ReceiptPublisher = field(
        default_factory=NoopReceiptPublisher
    )
    event_hooks: list[PaymentEventHook] = field(default_factory=list)
    default_payment_config: PaymentConfig | None = None


class HackPay:
    """
    Top-level application object. Wires components together and manages
    the FastAPI app state.
    """

    def __init__(self, config: HackPayConfig) -> None:
        self._config = config
        self._gate: PaymentGate | None = None

        # Add default structured logger if no hooks provided
        hooks = config.event_hooks or [LoggingPaymentEventHook()]
        self._hooks = hooks

    async def startup(self, app: object) -> None:
        """
        Initialise all components and attach the gate to app.state.

        Must be awaited inside the FastAPI lifespan context manager before
        the first request is served.

        Raises
        ------
        ConfigurationError, FacilitatorError
            If the provider cannot initialise (fail-fast at startup).
        """
        logger.info("HACK.Pay starting up...")
        await self._config.provider.initialize()

        self._gate = PaymentGate(
            provider=self._config.provider,
            idempotency_store=self._config.idempotency_store,
            receipt_publisher=self._config.receipt_publisher,
            event_hooks=self._hooks,
        )

        # Attach gate to FastAPI app state so decorators can access it
        if hasattr(app, "state"):
            app.state.hack_pay_gate = self._gate  # noqa: attr set dynamically

        logger.info("HACK.Pay started successfully")

    async def shutdown(self) -> None:
        """Release resources (closes HTTP client pool)."""
        logger.info("HACK.Pay shutting down...")
        await self._config.provider.close()
        logger.info("HACK.Pay shut down")

    @property
    def gate(self) -> PaymentGate:
        if self._gate is None:
            raise RuntimeError(
                "HackPay.startup() has not been called. "
                "Ensure it is awaited in the FastAPI lifespan."
            )
        return self._gate