# Basic FastAPI Example

A minimal example showing HACK.Pay with FastAPI.

## Setup

```bash
cp .env.example .env
# Edit .env — set HACK_PAY_RECEIVER_ACCOUNT_ID to your Hedera testnet account
pip install "hack-pay[fastapi]" uvicorn python-dotenv
```

## Run

```bash
uvicorn examples.basic_fastapi.main:app --reload
```

## Test

```bash
# Without payment — returns 402
curl -i http://localhost:8000/weather?city=London

# The PAYMENT-REQUIRED header contains Base64(JSON PaymentRequirements)
# Use an x402 v2 client to sign a Hedera TransferTransaction and retry
# with the PAYMENT-SIGNATURE header.
```

## Get testnet HBAR

Free testnet HBAR is available at the [Hedera Developer Portal](https://portal.hedera.com).