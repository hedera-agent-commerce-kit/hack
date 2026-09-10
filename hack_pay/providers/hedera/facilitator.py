"""
hack_pay.providers.hedera.facilitator â€” HTTP client for the x402 facilitator API.

This is the ONLY module in HACK.Pay that makes outbound HTTP calls.
All calls go through a single shared httpx.AsyncClient that is initialised
at startup and closed on shutdown (never per-request).

Facilitator endpoints (Blocky402 and x402.org):
  GET  /supported  â€” advertised networks and fee-payer accounts
  POST /verify     â€” validate a signed payment payload (no on-chain tx)
  POST /settle     â€” co-sign, submit, await SUCCESS
  GET  /health     â€” liveness check
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from hack_pay.errors import (
    FacilitatorInvalidResponseError,
    FacilitatorTimeoutError,
    FacilitatorUnavailableError,
)
from hack_pay.providers.hedera.types import (
    FacilitatorSupportedResponse,
    FacilitatorVerifyResponse,
)
from hack_pay.x402.types import PaymentPayload, PaymentRequirements, SettlementResponse

logger = logging.getLogger(__name__)


def _raise_for_facilitator(response: httpx.Response) -> None:
    """Map non-2xx facilitator responses to typed errors."""
    if response.status_code < 400:
        return
    try:
        detail = response.json().get("error") or response.text[:200]
    except Exception:
        detail = response.text[:200]
    raise FacilitatorInvalidResponseError(
        f"Facilitator returned HTTP {response.status_code}: {detail}"
    )


class FacilitatorClient:
    """
    Async HTTP client for a single x402 facilitator.

    Parameters
    ----------
    base_url:
        Facilitator base URL, e.g. ``"https://api.testnet.blocky402.com"``.
    timeout_seconds:
        Connect + read timeout. Default: 10 s.
    max_retries:
        Retry count on transient errors (5xx, timeout). Default: 2.
    backoff_seconds:
        Base sleep between retries (exponential: backoff * 2^attempt). Default: 0.5 s.
    """

    def __init__(
        self,
        base_url: str,
        timeout_seconds: int = 10,
        max_retries: int = 2,
        backoff_seconds: float = 0.5,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._max_retries = max_retries
        self._backoff = backoff_seconds
        self._http = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(timeout_seconds),
            limits=httpx.Limits(
                max_connections=20,
                max_keepalive_connections=10,
            ),
            headers={"Content-Type": "application/json"},
        )

    # â”€â”€ Public API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€  # noqa: E501

    async def get_supported(self) -> FacilitatorSupportedResponse:
        """Fetch advertised payment kinds and fee-payer accounts."""
        resp = await self._get_with_retry("/supported")
        try:
            return FacilitatorSupportedResponse.model_validate(resp.json())
        except Exception as exc:
            raise FacilitatorInvalidResponseError(
                f"Cannot parse /supported response: {exc}"
            ) from exc

    async def verify(
        self,
        payload: PaymentPayload,
        requirements: PaymentRequirements,
    ) -> FacilitatorVerifyResponse:
        """Validate the signed payment proof. Does NOT submit to Hedera."""
        body = {
            "payload": payload.model_dump(),
            "requirements": requirements.model_dump(),
        }
        resp = await self._post_with_retry("/verify", body)
        try:
            return FacilitatorVerifyResponse.model_validate(resp.json())
        except Exception as exc:
            raise FacilitatorInvalidResponseError(f"Cannot parse /verify response: {exc}") from exc

    async def settle(
        self,
        payload: PaymentPayload,
        requirements: PaymentRequirements,
    ) -> SettlementResponse:
        """Co-sign, submit, and await SUCCESS on the Hedera network."""
        body = {
            "payload": payload.model_dump(),
            "requirements": requirements.model_dump(),
        }
        resp = await self._post_with_retry("/settle", body)
        try:
            return SettlementResponse.model_validate(resp.json())
        except Exception as exc:
            raise FacilitatorInvalidResponseError(f"Cannot parse /settle response: {exc}") from exc

    async def health_check(self) -> bool:
        """Return True if the facilitator /health endpoint responds 200."""
        try:
            resp = await self._http.get("/health", timeout=3.0)
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        await self._http.aclose()

    # â”€â”€ Internal helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€  # noqa: E501

    async def _get_with_retry(self, path: str) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                resp = await self._http.get(path)
                _raise_for_facilitator(resp)
                return resp
            except httpx.TimeoutException as exc:
                last_exc = FacilitatorTimeoutError(f"Facilitator GET {path} timed out: {exc}")
            except httpx.ConnectError as exc:
                last_exc = FacilitatorUnavailableError(
                    f"Cannot connect to facilitator at {self._base_url}: {exc}"
                )
            except FacilitatorInvalidResponseError:
                raise  # non-retryable
            if attempt < self._max_retries:
                await asyncio.sleep(self._backoff * (2**attempt))
        raise last_exc  # type: ignore[misc]

    async def _post_with_retry(self, path: str, body: dict[str, Any]) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                resp = await self._http.post(path, json=body)
                _raise_for_facilitator(resp)
                return resp
            except httpx.TimeoutException as exc:
                last_exc = FacilitatorTimeoutError(f"Facilitator POST {path} timed out: {exc}")
            except httpx.ConnectError as exc:
                last_exc = FacilitatorUnavailableError(
                    f"Cannot connect to facilitator at {self._base_url}: {exc}"
                )
            except FacilitatorInvalidResponseError:
                raise  # non-retryable
            if attempt < self._max_retries:
                await asyncio.sleep(self._backoff * (2**attempt))
        raise last_exc  # type: ignore[misc]
