"""tests/unit/test_error_hierarchy.py — HackPayError hierarchy."""

from hack_pay.errors import (
    AssetMismatchError,
    ConfigurationError,
    DurableReceiptUnavailableError,
    FacilitatorError,
    FacilitatorInvalidResponseError,
    FacilitatorNetworkNotSupportedError,
    FacilitatorTimeoutError,
    FacilitatorUnavailableError,
    HackPayError,
    InsufficientPaymentError,
    InvalidPaymentError,
    MalformedPaymentError,
    NetworkMismatchError,
    OversizedPaymentHeaderError,
    PaymentError,
    ReceiptError,
    RecipientMismatchError,
    UnsupportedProtocolVersionError,
)


class TestHierarchy:
    def test_all_payment_errors_are_hack_pay_errors(self):
        for cls in [
            MalformedPaymentError,
            UnsupportedProtocolVersionError,
            InvalidPaymentError,
            InsufficientPaymentError,
            RecipientMismatchError,
            AssetMismatchError,
            NetworkMismatchError,
            OversizedPaymentHeaderError,
        ]:
            assert issubclass(cls, PaymentError)
            assert issubclass(cls, HackPayError)

    def test_all_facilitator_errors_are_hack_pay_errors(self):
        for cls in [
            FacilitatorUnavailableError,
            FacilitatorTimeoutError,
            FacilitatorNetworkNotSupportedError,
            FacilitatorInvalidResponseError,
        ]:
            assert issubclass(cls, FacilitatorError)
            assert issubclass(cls, HackPayError)

    def test_durable_receipt_error_hierarchy(self):
        assert issubclass(DurableReceiptUnavailableError, ReceiptError)
        assert issubclass(ReceiptError, HackPayError)

    def test_configuration_error_is_hack_pay_error(self):
        assert issubclass(ConfigurationError, HackPayError)


class TestErrorCodes:
    def test_each_error_has_unique_code(self):
        errors = [
            HackPayError,
            ConfigurationError,
            PaymentError,
            MalformedPaymentError,
            UnsupportedProtocolVersionError,
            InvalidPaymentError,
            InsufficientPaymentError,
            RecipientMismatchError,
            AssetMismatchError,
            NetworkMismatchError,
            OversizedPaymentHeaderError,
            FacilitatorError,
            FacilitatorUnavailableError,
            FacilitatorTimeoutError,
            FacilitatorNetworkNotSupportedError,
            FacilitatorInvalidResponseError,
            ReceiptError,
            DurableReceiptUnavailableError,
        ]
        codes = [e.code for e in errors]
        assert len(codes) == len(set(codes)), "Duplicate error codes found"

    def test_error_message_accessible(self):
        err = InvalidPaymentError("test message")
        assert str(err) == "test message"
        assert err.message == "test message"
        assert err.code == "INVALID_PAYMENT"

    def test_oversized_error_has_default_message(self):
        err = OversizedPaymentHeaderError()
        assert "64 KB" in err.message
