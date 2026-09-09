"""
HACK.Pay — Make any HTTP endpoint payable with x402 and Hedera.

Public API
----------
Everything a developer needs to import is available from this package root.
Internal modules are not part of the public API and may change without notice.

Quick start
-----------
    from contextlib import asynccontextmanager
    from fastapi import FastAPI
    from hack_pay import HackPay, HackPayConfig, paid
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

    @app.get("/weather")
    @paid("0.5 HBAR")
    async def get_weather(request):
        return {"forecast": "sunny"}
"""

from hack_pay.adapters.fastapi.app import HackPay, HackPayConfig
from hack_pay.adapters.fastapi.decorator import paid
from hack_pay.core.types import PaymentConfig
from hack_pay.errors import (
    AssetMismatchError,
    ConfigurationError,
    DurableReceiptUnavailableError,
    ExpiredPaymentError,
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
from hack_pay.idempotency import IdempotencyStore, InMemoryIdempotencyStore
from hack_pay.receipts.types import PaymentReceipt

__version__ = "0.1.0"

__all__ = [
    # Primary decorator
    "paid",
    # App wrapper
    "HackPay",
    "HackPayConfig",
    # Configuration
    "PaymentConfig",
    # Receipt
    "PaymentReceipt",
    # Idempotency
    "IdempotencyStore",
    "InMemoryIdempotencyStore",
    # Errors — base classes
    "HackPayError",
    "ConfigurationError",
    "PaymentError",
    "FacilitatorError",
    "ReceiptError",
    # Errors — payment protocol
    "MalformedPaymentError",
    "UnsupportedProtocolVersionError",
    "InvalidPaymentError",
    "InsufficientPaymentError",
    "RecipientMismatchError",
    "AssetMismatchError",
    "NetworkMismatchError",
    "ExpiredPaymentError",
    "OversizedPaymentHeaderError",
    # Errors — facilitator
    "FacilitatorUnavailableError",
    "FacilitatorTimeoutError",
    "FacilitatorNetworkNotSupportedError",
    "FacilitatorInvalidResponseError",
    # Errors — receipts
    "DurableReceiptUnavailableError",
    # Version
    "__version__",
]