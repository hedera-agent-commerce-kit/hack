"""hack_pay.adapters.fastapi.decorator - @paid decorator."""
from __future__ import annotations
import functools
from typing import Any, Callable
from fastapi import Request
from fastapi.responses import JSONResponse, Response
from hack_pay.adapters.fastapi.errors import error_to_response
from hack_pay.core.gate import PaymentGate
from hack_pay.core.types import PaymentConfig, RequestContext
from hack_pay.errors import OversizedPaymentHeaderError
from hack_pay.providers.hedera.amounts import parse_hbar_string
from hack_pay.x402.codec import encode_payment_required, encode_payment_response
from hack_pay.x402.types import SettlementResponse

_HACK_PAY_CONFIG_ATTR = "__hack_pay_config__"


def paid(amount: str | PaymentConfig) -> Callable[..., Any]:
    """Gate a FastAPI route behind an x402 payment. Usage: @paid("0.5 HBAR")"""
    config = _parse_config(amount)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        setattr(func, _HACK_PAY_CONFIG_ATTR, config)

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Response:
            request = _extract_request(args, kwargs)
            if request is None:
                raise RuntimeError(
                    f"@paid requires 'request: Request' in the handler signature. "
                    f"Add it to {func.__name__}()."
                )
            gate: PaymentGate = request.app.state.hack_pay_gate
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
                    headers={"PAYMENT-REQUIRED": encode_payment_required(result.requirements)},
                )
            if result.kind == "error":
                return error_to_response(result.error)
            # Granted - call handler then inject PAYMENT-RESPONSE header
            raw = await func(*args, **kwargs)
            settlement = SettlementResponse(
                success=True,
                transaction=result.receipt.transaction_id,
                network=result.receipt.network,
                payer=result.receipt.payer_account_id,
            )
            header_val = encode_payment_response(settlement)
            if isinstance(raw, Response):
                raw.headers["PAYMENT-RESPONSE"] = header_val
                return raw
            return JSONResponse(content=raw, headers={"PAYMENT-RESPONSE": header_val})

        return wrapper
    return decorator


def _parse_config(amount: str | PaymentConfig) -> PaymentConfig:
    if isinstance(amount, PaymentConfig):
        return amount
    if isinstance(amount, str):
        return PaymentConfig(amount_tinybars=parse_hbar_string(amount))
    raise TypeError(f"@paid expects '0.5 HBAR' or PaymentConfig, got {type(amount).__name__!r}")


def _extract_request(args: tuple[Any, ...], kwargs: dict[str, Any]) -> Request | None:
    for arg in args:
        if isinstance(arg, Request):
            return arg
    for val in kwargs.values():
        if isinstance(val, Request):
            return val
    return None