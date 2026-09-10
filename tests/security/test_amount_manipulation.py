"""tests/security/test_amount_manipulation.py — Amount is server-side only."""

import pytest
from pydantic import ValidationError

from hack_pay.core.types import PaymentConfig
from hack_pay.x402.types import PaymentRequirements


class TestAmountManipulation:
    def test_requirements_amount_comes_from_config_not_request(self):
        # The amount in PaymentRequirements must match PaymentConfig.amount_tinybars
        # It is NEVER derived from request headers or body
        config = PaymentConfig(amount_tinybars=50_000_000, network="hedera:testnet")
        req = PaymentRequirements(
            scheme="exact",
            network="hedera:testnet",
            pay_to="0.0.12345",
            amount=str(config.amount_tinybars),
        )
        assert req.amount == "50000000"
        assert int(req.amount) == config.amount_tinybars

    def test_cannot_construct_zero_amount_requirement(self):
        with pytest.raises(ValidationError):
            PaymentRequirements(
                scheme="exact", network="hedera:testnet", pay_to="0.0.12345", amount="0"
            )

    def test_cannot_construct_negative_amount_requirement(self):
        with pytest.raises(ValidationError):
            PaymentRequirements(
                scheme="exact", network="hedera:testnet", pay_to="0.0.12345", amount="-100"
            )

    def test_amount_must_be_integer_string(self):
        with pytest.raises(ValidationError):
            PaymentRequirements(
                scheme="exact", network="hedera:testnet", pay_to="0.0.12345", amount="0.5"
            )
