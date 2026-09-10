"""
hack_pay.observability.logging â€” Structured logging PaymentEventHook.

Emits one JSON-structured log line per payment lifecycle event.
Uses WARNING for failure events, INFO for everything else.
"""

from __future__ import annotations

import logging

from hack_pay.observability.base import PaymentEvent, PaymentEventContext, PaymentEventHook


class LoggingPaymentEventHook(PaymentEventHook):
    """
    Writes structured payment lifecycle events to a Python logger.

    Parameters
    ----------
    logger_name:
        Logger name. Defaults to ``"hack_pay.payments"``.
        Configure handlers and formatters via standard logging config.
    """

    _FAILURE_EVENTS = {PaymentEvent.VERIFY_FAILURE, PaymentEvent.SETTLE_FAILURE}

    def __init__(self, logger_name: str = "hack_pay.payments") -> None:
        self._logger = logging.getLogger(logger_name)

    async def on_event(self, ctx: PaymentEventContext) -> None:
        record: dict[str, Any] = {
            "event": ctx.event.value,
            "endpoint": ctx.endpoint,
        }
        # Only include fields that are set â€” keeps logs clean
        if ctx.amount_tinybars is not None:
            record["amount_tinybars"] = ctx.amount_tinybars
        if ctx.network is not None:
            record["network"] = ctx.network
        if ctx.transaction_id is not None:
            record["transaction_id"] = ctx.transaction_id  # safe to log
        if ctx.error_type is not None:
            record["error_type"] = ctx.error_type
        if ctx.duration_ms is not None:
            record["duration_ms"] = round(ctx.duration_ms, 2)
        if ctx.extra:
            record["extra"] = ctx.extra

        level = logging.WARNING if ctx.event in self._FAILURE_EVENTS else logging.INFO
        self._logger.log(level, "hack_pay.event", extra=record)