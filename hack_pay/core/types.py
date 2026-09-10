"""
hack_pay.core.types — Core value types used by PaymentGate and adapters.

Dependency rule: no fastapi, starlette, httpx, or chain SDK imports here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from hack_pay.errors import HackPayError
    from hack_pay.receipts.types import PaymentReceipt
    from hack_pay.x402.types import PaymentRequirements


# ── PaymentConfig (per-endpoint) ─────────────────────────────────────────────


@dataclass(frozen=True)
class PaymentConfig:
    """
    Per-endpoint payment configuration attached by the @paid decorator.

    Attributes
    ----------
    amount_tinybars:
        Exact integer tinybar amount (1 HBAR = 100_000_000 tinybars).
        Always an integer — never float.
    asset:
        ``"0.0.0"`` for native HBAR. HTS fungible token entity ID for tokens.
    network:
        CAIP-2 network identifier, e.g. ``"hedera:testnet"``.
    description:
        Human-readable endpoint description shown in payment prompts.
    max_deadline_seconds:
        Window within which the client must submit payment after receiving
        the 402 challenge. Default: 300 s (5 minutes).
    require_durable_receipt:
        If True, the gate rejects the request when the ReceiptPublisher
        backend is unavailable. Default: False (non-blocking publish).
    """

    amount_tinybars: int
    asset: str = "0.0.0"
    network: str = "hedera:testnet"
    description: str = ""
    max_deadline_seconds: int = 300
    require_durable_receipt: bool = False


# ── RequestContext ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RequestContext:
    """
    Framework-agnostic snapshot of the inbound HTTP request.

    Populated by the FastAPI adapter before calling PaymentGate.gate().
    Contains only the fields PaymentGate needs — no FastAPI types leak
    into the core layer.
    """

    endpoint: str  # URL path, e.g. "/weather"
    method: str  # HTTP method, e.g. "GET"
    payment_signature: str | None = None  # raw PAYMENT-SIGNATURE header value
    client_host: str | None = None  # IP address for logging only


# ── GateResult union ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ChallengeResult:
    """Gate result: no payment proof present — issue a 402 challenge."""

    kind: Literal["challenge"] = field(default="challenge", init=False)
    requirements: PaymentRequirements = field(default=None)  # type: ignore[assignment]


@dataclass(frozen=True)
class GrantedResult:
    """Gate result: payment verified and settled — allow the request."""

    kind: Literal["granted"] = field(default="granted", init=False)
    receipt: PaymentReceipt = field(default=None)  # type: ignore[assignment]


@dataclass(frozen=True)
class ErrorResult:
    """Gate result: payment was rejected or a provider error occurred."""

    kind: Literal["error"] = field(default="error", init=False)
    error: HackPayError = field(default=None)  # type: ignore[assignment]


GateResult = ChallengeResult | GrantedResult | ErrorResult
