"""
hack_pay.core.gate — PaymentGate: the central payment orchestrator.

PaymentGate is the only component that coordinates all other components.
It has no HTTP knowledge (no fastapi/starlette imports) and no blockchain
knowledge (no hedera SDK imports).

Flow
----
1. No PAYMENT-SIGNATURE header  →  build requirements  →  ChallengeResult
2. PAYMENT-SIGNATURE present:
   a. Check idempotency store (fast path for replays)
   b. Validate payload structure against requirements
   c. Acquire per-key in-flight lock (prevents concurrent double-settle)
   d. Re-check idempotency (double-check after lock acquisition)
   e. Verify with provider
   f. Settle with provider
   g. Store in idempotency store (put_if_absent — atomic)
   h. Publish receipt (non-blocking unless require_durable=True)
   i. Emit lifecycle events
   j. Return GrantedResult
"""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncIterator

from hack_pay.core.types import (
    ChallengeResult,
    ErrorResult,
    GateResult,
    GrantedResult,
    PaymentConfig,
    RequestContext,
)
from hack_pay.errors import (
    DurableReceiptUnavailableError,
    FacilitatorError,
    HackPayError,
    InvalidPaymentError,
    MalformedPaymentError,
)
from hack_pay.idempotency.base import IdempotencyStore
from hack_pay.idempotency.keys import derive_idempotency_key
from hack_pay.observability.base import (
    PaymentEvent,
    PaymentEventContext,
    PaymentEventHook,
)
from hack_pay.providers.base import PaymentProvider
from hack_pay.receipts.base import ReceiptPublisher
from hack_pay.receipts.types import PaymentReceipt
from hack_pay.x402.codec import decode_payment_signature
from hack_pay.x402.types import PaymentPayload, PaymentRequirements
from hack_pay.x402.validation import validate_payload_matches_requirements

logger = logging.getLogger(__name__)

# Maximum number of concurrent in-flight keys tracked in the lock map.
_MAX_INFLIGHT_LOCKS = 10_000


class PaymentGate:
    """
    Central payment orchestrator.

    Parameters
    ----------
    provider:
        Initialised PaymentProvider (e.g. HederaPaymentProvider).
    idempotency_store:
        Store for settled payment receipts (prevents double-settlement).
    receipt_publisher:
        Optional durable receipt recorder (default: NoopReceiptPublisher).
    event_hooks:
        List of PaymentEventHook instances for structured lifecycle logging.
    """

    def __init__(
        self,
        provider: PaymentProvider,
        idempotency_store: IdempotencyStore,
        receipt_publisher: ReceiptPublisher,
        event_hooks: list[PaymentEventHook] | None = None,
    ) -> None:
        self._provider = provider
        self._idempotency = idempotency_store
        self._receipt_publisher = receipt_publisher
        self._hooks: list[PaymentEventHook] = event_hooks or []
        # Per-key asyncio locks prevent concurrent double-settle.
        self._inflight: dict[str, asyncio.Lock] = {}
        self._inflight_meta_lock = asyncio.Lock()

    # ── Primary entry point ───────────────────────────────────────────────

    async def gate(
        self,
        context: RequestContext,
        config: PaymentConfig,
    ) -> GateResult:
        """
        Evaluate whether the request should be granted or challenged.

        Never raises — all errors are wrapped in ErrorResult so the adapter
        can map them to the correct HTTP status without bare exception handling.
        """
        try:
            return await self._gate(context, config)
        except HackPayError as exc:
            return ErrorResult(error=exc)
        except Exception as exc:
            # Unexpected errors must not leak internals to the HTTP response.
            logger.exception("Unexpected error in PaymentGate.gate()")
            return ErrorResult(
                error=InvalidPaymentError(
                    "An unexpected error occurred during payment processing."
                )
            )

    # ── Internal implementation ───────────────────────────────────────────

    async def _gate(
        self,
        context: RequestContext,
        config: PaymentConfig,
    ) -> GateResult:
        # ── Phase 1: No payment proof → issue challenge ───────────────────
        if not context.payment_signature:
            requirements = await self._provider.build_payment_requirements(config)
            await self._emit(PaymentEvent.CHALLENGE_ISSUED, context, config)
            return ChallengeResult(requirements=requirements)

        # ── Phase 2: Parse and validate the payment signature ─────────────
        payload = decode_payment_signature(context.payment_signature)
        requirements = await self._provider.build_payment_requirements(config)
        validate_payload_matches_requirements(payload, requirements)

        key = derive_idempotency_key(payload)

        # Fast path: already settled (idempotent replay)
        if cached := await self._idempotency.get(key):
            await self._emit(PaymentEvent.IDEMPOTENCY_HIT, context, config)
            return GrantedResult(receipt=cached)

        # ── Phase 3: Verify + settle under per-key lock ───────────────────
        async with self._inflight_lock(key):
            # Re-check after acquiring lock (concurrent duplicate may have settled)
            if cached := await self._idempotency.get(key):
                await self._emit(PaymentEvent.IDEMPOTENCY_HIT, context, config)
                return GrantedResult(receipt=cached)

            # Verify
            await self._emit(PaymentEvent.VERIFY_START, context, config)
            t0 = time.monotonic()
            verify_result = await self._provider.verify(payload, requirements)
            verify_ms = (time.monotonic() - t0) * 1000

            if not verify_result.ok:
                await self._emit(
                    PaymentEvent.VERIFY_FAILURE, context, config,
                    error_type="InvalidPaymentError", duration_ms=verify_ms,
                )
                raise InvalidPaymentError(
                    f"Payment verification failed: {verify_result.reason}"
                )
            await self._emit(
                PaymentEvent.VERIFY_SUCCESS, context, config,
                duration_ms=verify_ms,
            )

            # Settle
            await self._emit(PaymentEvent.SETTLE_START, context, config)
            t1 = time.monotonic()
            settle_result = await self._provider.settle(payload, requirements)
            settle_ms = (time.monotonic() - t1) * 1000

            if not settle_result.ok:
                await self._emit(
                    PaymentEvent.SETTLE_FAILURE, context, config,
                    error_type="FacilitatorError", duration_ms=settle_ms,
                )
                raise FacilitatorError(
                    f"Payment settlement failed: {settle_result.reason}"
                )

            receipt = PaymentReceipt(
                transaction_id=settle_result.transaction_id,
                payer_account_id=settle_result.payer,
                receiver_account_id=requirements.pay_to,
                amount_tinybars=int(requirements.amount),
                asset=requirements.asset,
                network=requirements.network,
                settled_at=datetime.now(tz=timezone.utc),
                facilitator_url=self._provider._config.facilitator_url  # type: ignore[attr-defined]
                if hasattr(self._provider, "_config") else "",
            )

            await self._idempotency.put_if_absent(
                key, receipt,
                ttl_seconds=config.max_deadline_seconds + 3600,
            )

            await self._emit(
                PaymentEvent.SETTLE_SUCCESS, context, config,
                transaction_id=receipt.transaction_id,
                duration_ms=settle_ms,
            )

        # ── Phase 4: Non-blocking receipt publication ─────────────────────
        if config.require_durable_receipt:
            if not await self._receipt_publisher.is_available():
                raise DurableReceiptUnavailableError()
            await self._receipt_publisher.publish(receipt)
            await self._emit(PaymentEvent.RECEIPT_PUBLISHED, context, config)
        else:
            asyncio.create_task(self._safe_publish(receipt, context, config))

        return GrantedResult(receipt=receipt)

    # ── Helpers ───────────────────────────────────────────────────────────

    @asynccontextmanager
    async def _inflight_lock(self, key: str) -> AsyncIterator[None]:
        """Acquire a per-key asyncio.Lock to prevent concurrent double-settle."""
        async with self._inflight_meta_lock:
            if key not in self._inflight:
                # Evict oldest locks if the map is too large
                if len(self._inflight) >= _MAX_INFLIGHT_LOCKS:
                    oldest = next(iter(self._inflight))
                    del self._inflight[oldest]
                self._inflight[key] = asyncio.Lock()
            lock = self._inflight[key]
        async with lock:
            yield
        # Clean up after release so the map doesn't grow unboundedly
        async with self._inflight_meta_lock:
            self._inflight.pop(key, None)

    async def _safe_publish(
        self,
        receipt: PaymentReceipt,
        context: RequestContext,
        config: PaymentConfig,
    ) -> None:
        """Fire-and-forget receipt publish that never propagates errors."""
        try:
            await self._receipt_publisher.publish(receipt)
            await self._emit(PaymentEvent.RECEIPT_PUBLISHED, context, config)
        except Exception:
            logger.exception("ReceiptPublisher.publish() failed (non-fatal)")

    async def _emit(
        self,
        event: PaymentEvent,
        context: RequestContext,
        config: PaymentConfig,
        transaction_id: str | None = None,
        error_type: str | None = None,
        duration_ms: float | None = None,
    ) -> None:
        """Emit a lifecycle event to all registered hooks. Never raises."""
        ctx = PaymentEventContext(
            event=event,
            endpoint=context.endpoint,
            amount_tinybars=config.amount_tinybars,
            network=config.network,
            transaction_id=transaction_id,
            error_type=error_type,
            duration_ms=duration_ms,
        )
        for hook in self._hooks:
            try:
                await hook.on_event(ctx)
            except Exception:
                logger.exception("PaymentEventHook.on_event() raised unexpectedly")