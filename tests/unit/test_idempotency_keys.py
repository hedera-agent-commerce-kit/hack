"""Idempotency keys bind a proof to its endpoint payment requirements."""

import base64

from hack_pay.idempotency.keys import derive_idempotency_key
from hack_pay.x402.types import PaymentPayload, PaymentRequirements


def test_key_changes_when_endpoint_terms_change() -> None:
    payload = PaymentPayload(
        scheme="exact", network="hedera:testnet", payload=base64.b64encode(b"same-proof").decode()
    )
    base = PaymentRequirements(
        scheme="exact", network="hedera:testnet", pay_to="0.0.12345", amount="1", asset="0.0.0"
    )

    keys = {
        derive_idempotency_key(payload, base),
        derive_idempotency_key(payload, base.model_copy(update={"amount": "2"})),
        derive_idempotency_key(payload, base.model_copy(update={"asset": "0.0.456"})),
        derive_idempotency_key(payload, base.model_copy(update={"pay_to": "0.0.999"})),
        derive_idempotency_key(payload, base.model_copy(update={"network": "hedera:mainnet"})),
        derive_idempotency_key(payload, base.model_copy(update={"scheme": "other"})),
    }

    assert len(keys) == 6
