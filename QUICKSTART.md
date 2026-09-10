# QUICKSTART — HACK.Pay

Get a paid FastAPI endpoint running in under 10 minutes.

---

## Prerequisites

- Python 3.10 or newer
- A Hedera testnet account — create one free at [portal.hedera.com](https://portal.hedera.com)
- Your testnet account funded with free testnet HBAR (the portal gives you some on signup)

You do **not** need to register with any payment processor or create an API key.

---

## 1. Install

```bash
pip install "hack-pay[fastapi]" uvicorn python-dotenv
```

---

## 2. Configure `.env`

Create a file named `.env` in your project directory:

```dotenv
HACK_PAY_HEDERA_NETWORK=testnet
HACK_PAY_RECEIVER_ACCOUNT_ID=0.0.YOUR_ACCOUNT_ID
HACK_PAY_FACILITATOR_URL=https://api.testnet.blocky402.com
HACK_PAY_IDEMPOTENCY_BACKEND=memory
HACK_PAY_LOG_LEVEL=INFO
```

| Variable | What it does |
|---|---|
| `HACK_PAY_HEDERA_NETWORK` | Which Hedera network to use. `testnet` for development, `mainnet` for production. |
| `HACK_PAY_RECEIVER_ACCOUNT_ID` | The Hedera account that receives HBAR payments — your wallet, e.g. `0.0.12345`. |
| `HACK_PAY_FACILITATOR_URL` | The Blocky402 facilitator that verifies and settles payments. No API key needed. |
| `HACK_PAY_IDEMPOTENCY_BACKEND` | Replay-protection store. `memory` is fine for local development. |
| `HACK_PAY_LOG_LEVEL` | Log verbosity. `INFO` is a good default. |

---

## 3. Write your first paid endpoint

Create `main.py`:

```python
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request

from hack_pay import HackPay, HackPayConfig, paid
from hack_pay.providers.hedera import HederaPaymentProvider, HederaProviderConfig

load_dotenv()  # reads .env

# ── Provider setup ─────────────────────────────────────────────────────────

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

# ── Lifespan: connect on startup, clean up on shutdown ────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await hack.startup(app)
    yield
    await hack.shutdown()

app = FastAPI(lifespan=lifespan)

# ── Paid route ────────────────────────────────────────────────────────────

@app.get("/weather")
@paid("0.5 HBAR")
async def get_weather(city: str, request: Request):  # <-- request: Request is required
    return {
        "city": city,
        "forecast": "sunny",
        "temperature_c": 22,
        "note": "Paid for with 0.5 HBAR via x402.",
    }

# ── Free route ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}
```

> [!WARNING]
> **`request: Request` is required in every `@paid` handler.**
>
> The `@paid` decorator locates the FastAPI `Request` object by inspecting the handler's
> arguments at call time. If `request: Request` is not present in the function signature,
> the decorator raises a `RuntimeError` on the first real request:
>
> ```
> @paid requires 'request: Request' in the handler signature. Add it to get_weather().
> ```
>
> Always include `request: Request` as a parameter, even if you don't use it in the handler body.
> Import it from `fastapi`: `from fastapi import FastAPI, Request`.

---

## 4. Run the server

```bash
uvicorn main:app --reload
```

You should see output similar to:

```
INFO:     Started server process [...]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

---

## 5. Test with curl

### Without payment — you get a 402

```bash
curl -i http://localhost:8000/weather?city=London
```

Expected response:

```
HTTP/1.1 402 Payment Required
PAYMENT-REQUIRED: <base64-encoded payment requirements>
content-type: application/json

{"error":"Payment Required","x402Version":2}
```

The `PAYMENT-REQUIRED` header is a Base64-encoded description of what the server expects:
network, amount, receiver account, and expiry.

### Decode the header to inspect it

```bash
curl -s http://localhost:8000/weather?city=London \
  | python3 -c "import sys,base64,json; h=input(); print(json.dumps(json.loads(base64.b64decode(h)), indent=2))"
```

Or with the header value directly:

```bash
VALUE=$(curl -si http://localhost:8000/weather?city=London \
  | grep -i 'PAYMENT-REQUIRED:' \
  | awk '{print $2}' \
  | tr -d '\r')
echo "$VALUE" | base64 -d | python3 -m json.tool
```

### Make a real payment

Sending a real payment requires an x402-compatible client that can build and sign a Hedera
`TransferTransaction`. The client attaches the Base64 signature as a `PAYMENT-SIGNATURE`
header on the retry request.

See [x402.org](https://x402.org) for compatible client libraries. The TypeScript client
(`@x402/hedera`) works directly with Hedera testnet.

### Successful response (after payment)

When a valid `PAYMENT-SIGNATURE` header is present and verified, the server returns `200`
and includes a `PAYMENT-RESPONSE` header:

```
HTTP/1.1 200 OK
PAYMENT-RESPONSE: <base64-encoded settlement receipt>
content-type: application/json

{"city": "London", "forecast": "sunny", "temperature_c": 22, ...}
```

The `PAYMENT-RESPONSE` header contains the Hedera transaction ID for the settled payment.
Decode it the same way as `PAYMENT-REQUIRED` to extract the `transaction` field, then
verify it at [hashscan.io](https://hashscan.io).

---

## How the payment flow works

```
Client                    Your server             Blocky402 (facilitator)
  │                           │                           │
  │── GET /weather ──────────►│                           │
  │                           │ (no PAYMENT-SIGNATURE)    │
  │◄── 402 + PAYMENT-REQUIRED─│                           │
  │                           │                           │
  │  [client builds and signs a Hedera TransferTransaction]
  │                           │                           │
  │── GET /weather ───────────│                           │
  │   PAYMENT-SIGNATURE: ...  │                           │
  │                           │── verify + settle ───────►│
  │                           │◄── confirmed ─────────────│
  │◄── 200 + PAYMENT-RESPONSE─│                           │
```

1. Your server returns `402` with a `PAYMENT-REQUIRED` header describing the requirements.
2. The client builds a Hedera `TransferTransaction`, signs it, and sends the proof as `PAYMENT-SIGNATURE`.
3. Your server forwards it to Blocky402, which verifies and settles the transaction on Hedera.
4. Your server returns `200` with a `PAYMENT-RESPONSE` header containing the Hedera transaction ID.

---

## Next steps

- **[README.md](./README.md)** — library overview, configuration reference, error types
- **[examples/basic_fastapi/](./examples/basic_fastapi/)** — the full working example used in this guide
- **[ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)** — layer diagram and full payment-flow sequence
- **[Blocky402 docs](https://blocky402.com)** — facilitator API reference, mainnet setup
- **[HashScan](https://hashscan.io)** — verify any Hedera transaction ID from `PAYMENT-RESPONSE`
- **[Hedera portal](https://portal.hedera.com)** — manage your testnet and mainnet accounts
