"""
hack_pay.adapters.fastapi.decorator — @paid decorator and helpers.

This is the primary developer-facing integration point.

Usage
-----
    from hack_pay import paid

    @app.get("/weather")
    @paid("0.5 HBAR")
    async def get_weather(city: str, request: Request):
        return {"forecast": "sunny"}

The decorator:
1. Parses the amount string / PaymentConfig at decoration time (startup fail-fast).
2. Wraps the handler to call PaymentGate.gate() before the handler runs.
3. Returns a 402 response if no payment proof is present.
4. Returns a safe error response if the proof is invalid.
5. Injects the PAYMENT-RESPONSE header on success and calls the real handler.

FastAPI requires ``request: Request`` to be in the handler signature so the
adapter can extract headers.  The decorator passes it through transparently.
"""

from __future__ import annotations

import functools
import inspect
from typing import Any, Callable

from fastapi import Request
from fastapi.responses import JSONResponse, Response

from hack_pay.adapters.fastapi.errors import error_to_response
from hack_pay.core.gate import PaymentGate
from hack_pay.core.types import PaymentConfig, RequestContext
from hack_pay.errors import HackPayError, OversizedPaymentHeaderError
from hack_pay.providers.hedera.amounts import parse_hbar_string
from hack_pay.x402.codec import encode_payment_required, encode_payment_response
from hack_pay.x402.types import SettlementResponse

_HACK_PAY_CONFIG_ATTR = "__hack_pay_config__"


def paid(amount: str | PaymentConfig) -> Callable:
    """
    Decorator that gates a FastAPI route handler behind an x402 payment.

    Parameters
    ----------
    amount:
        Either a string like ``"0.5 HBAR"`` or a fully-constructed
        ``PaymentConfig`` for advanced configuration.

    Returns
    -------
    Callable
        A decorator that wraps the route handler.

    Raises
    ------
    ValueError
        At decoration time if the amount string is invalid (fail-fast).
    """
    config = _parse_config(amount)

    def decorator(func: Callable) -> Callable:
        # Attach config for introspection (tests, documentation generators)
        setattr(func, _HACK_PAY_CONFIG_ATTR, config)

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Response:
            # Extract the FastAPI Request from positional or keyword args
            request = _extract_request(args, kwargs)
            if request is None:
                raise RuntimeError(
                    f"@paid requires 'request: Request' in the handler signature. "
                    f"Add it to {func.__name__}()."
                )

            gate: PaymentGate = request.app.state.hack_pay_gate

            # Check header size before building context (DoS guard)
            sig_header = (
                request.headers.get("payment-signature")
                or request.headers.get("PAYMENT-SIGNATURE")
            )
            if sig_header and len(sig_header.encode()) > 65_536:
                return error_to_response(OversizedPaymentHeaderError())

            context = RequestContext(
                endpoint=str(request.url.path),
                method=request.method,
                payment_signature=sig_header,
                client_host=request.client.host if request.client else None,
            )

            result = await gate.gate(context, config)

            if result.kind == "challenge":
                return JSONResponse(
                    status_code=402,
                    content={"error": "Payment Required", "x402Version": 2},
                    headers={
                        "PAYMENT-REQUIRED": encode_payment_required(result.requirements)
                    },
                )

            if result.kind == "error":
                return error_to_response(result.error)

            # Granted — call the real handler
            response = await func(*args, **kwargs)

            # Inject PAYMENT-RESPONSE header with settlement details
            if isinstance(response, Response) and response.headers is not None:
                settlement = SettlementResponse(
                    success=True,
                    transaction=result.receipt.transaction_id,
                    network=result.receipt.network,
                    payer=result.receipt.payer_account_id,
                )
                response.headers["PAYMENT-RESPONSE"] = encode_payment_response(settlement)

            return response

        return wrapper

    return decorator


def _parse_config(amount: str | PaymentConfig) -> PaymentConfig:
    """Convert amount string or PaymentConfig to a validated PaymentConfig."""
    if isinstance(amount, PaymentConfig):
        return amount
    if isinstance(amount, str):
        tinybars = parse_hbar_string(amount)
        return PaymentConfig(amount_tinybars=tinybars)
    raise TypeError(
        f"@paid expects a string like '0.5 HBAR' or a PaymentConfig, "
        f"got {type(amount).__name__!r}"
    )


def _extract_request(args: tuple, kwargs: dict) -> Request | None:
    """Find the FastAPI Request object in handler arguments."""
    for arg in args:
        if isinstance(arg, Request):
            return arg
    for val in kwargs.values():
        if isinstance(val, Request):
            return val
    return None