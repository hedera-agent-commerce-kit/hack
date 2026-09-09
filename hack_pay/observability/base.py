"""
hack_pay.observability.base — PaymentEventHook interface and event types.

Hooks are called by PaymentGate at each lifecycle stage.  A hook must never
raise — failures are caught and logged internally so a broken hook cannot
affect the payment outcome.

Log safety rule: PaymentEventContext must never include raw payment
signatures, private keys, or full transaction bytes.  Only the Hedera
transaction_id returned after settlement is safe to log.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class PaymentEvent(str, Enum):
    """Lifecycle events emitted by PaymentGate."""

    CHALLENGE_ISSUED = "challenge_issued"
    VERIFY_START = "verify_start"
    VERIFY_SUCCESS = "verify_success"
    VERIFY_FAILURE = "verify_failure"
    SETTLE_START = "settle_start"
    SETTLE_SUCCESS = "settle_success"
    SETTLE_FAILURE = "settle_failure"
    RECEIPT_PUBLISHED = "receipt_published"
    IDEMPOTENCY_HIT = "idempotency_hit"
    REPLAY_DETECTED = "replay_detected"


@dataclass(frozen=True)
class PaymentEventContext:
    """
    Structured context passed to every PaymentEventHook.on_event() call.

    Fields are optional so each event only carries the data available at
    that stage of the lifecycle.

    NEVER add: payment payload bytes, private keys, or full signatures.
    """

    event: PaymentEvent
    endpoint: str
    amount_tinybars: int | None = None
    network: str | None = None
    transaction_id: str | None = None  # safe — Hedera tx id, not a secret
    error_type: str | None = None       # error class name only, not message
    duration_ms: float | None = None
    extra: dict = field(default_factory=dict)


class PaymentEventHook(ABC):
    """Abstract base for payment lifecycle event observers."""

    @abstractmethod
    async def on_event(self, ctx: PaymentEventContext) -> None:
        """
        Handle a payment lifecycle event.

        Must not raise under any circumstances.  Implementations should
        catch and log their own internal errors.
        """