"""tests/security/test_log_leakage.py — Sensitive data must not appear in logs."""

import base64, json, logging, pytest
from hack_pay.observability.base import PaymentEvent, PaymentEventContext
from hack_pay.observability.logging import LoggingPaymentEventHook


PRIVATE_KEY_PATTERN = "302e020100300506032b657004"
FULL_SIGNATURE = base64.b64encode(b"secret-tx-bytes-never-log-this").decode()


@pytest.mark.asyncio
class TestLogLeakage:
    async def test_event_hook_does_not_log_payment_payload(self, caplog):
        hook = LoggingPaymentEventHook()
        ctx = PaymentEventContext(
            event=PaymentEvent.SETTLE_SUCCESS,
            endpoint="/test",
            transaction_id="0.0.1@100.0",  # safe
        )
        with caplog.at_level(logging.INFO):
            await hook.on_event(ctx)
        for record in caplog.records:
            log_text = str(record.__dict__)
            assert PRIVATE_KEY_PATTERN not in log_text
            assert FULL_SIGNATURE not in log_text

    async def test_transaction_id_is_safe_to_log(self, caplog):
        hook = LoggingPaymentEventHook()
        ctx = PaymentEventContext(
            event=PaymentEvent.SETTLE_SUCCESS,
            endpoint="/test",
            transaction_id="0.0.12345@1725000000.000000000",
        )
        with caplog.at_level(logging.INFO):
            await hook.on_event(ctx)
        # transaction_id is explicitly allowed in logs
        found = any("0.0.12345" in str(r.__dict__) for r in caplog.records)
        assert found