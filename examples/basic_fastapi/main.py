"""
examples/basic_fastapi/main.py — Minimal HACK.Pay + FastAPI example.

Run
---
    cp .env.example .env
    # Edit .env: set HACK_PAY_RECEIVER_ACCOUNT_ID to your testnet account
    pip install "hack-pay[fastapi]" uvicorn
    uvicorn examples.basic_fastapi.main:app --reload

Test (no payment)
-----------------
    curl http://localhost:8000/weather?city=London
    # Returns: 402 Payment Required + PAYMENT-REQUIRED header

The PAYMENT-REQUIRED header contains Base64-encoded PaymentRequirements.
Use an x402-compatible client (e.g. @x402/hedera TypeScript client) to
sign a TransferTransaction and retry with the PAYMENT-SIGNATURE header.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from hack_pay import HackPay, HackPayConfig, paid
from hack_pay.providers.hedera import HederaPaymentProvider, HederaProviderConfig

# ── Provider setup ────────────────────────────────────────────────────────────

provider = HederaPaymentProvider(
    HederaProviderConfig(
        network=os.environ.get("HACK_PAY_HEDERA_NETWORK", "hedera:testnet"),
        receiver_account_id=os.environ["HACK_PAY_RECEIVER_ACCOUNT_ID"],
        facilitator_url=os.environ.get(
            "HACK_PAY_FACILITATOR_URL",
            "https://api.testnet.blocky402.com",
        ),
    )
)

hack = HackPay(HackPayConfig(provider=provider))

# ── FastAPI app with lifespan ─────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await hack.startup(app)   # initialises provider, fetches feePayer
    yield
    await hack.shutdown()     # closes HTTP connection pool


app = FastAPI(
    title="HACK.Pay Basic Example",
    version="0.1.0",
    lifespan=lifespan,
)

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/weather")
@paid("0.5 HBAR")
async def get_weather(city: str, request: Request):
    """
    Returns weather data for a city. Costs 0.5 HBAR per call.

    Without a valid PAYMENT-SIGNATURE header, returns HTTP 402 with
    the PAYMENT-REQUIRED challenge header.
    """
    return {
        "city": city,
        "forecast": "sunny",
        "temperature_c": 22,
        "note": "This response was paid for with 0.5 HBAR via x402.",
    }


@app.get("/health")
async def health():
    """Free endpoint — no payment required."""
    return {"status": "ok"}