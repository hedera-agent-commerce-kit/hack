<div align="center">

# HACK.Pay

**Make any HTTP endpoint payable — one decorator, Hedera, no billing infrastructure.**

[![CI](https://github.com/hedera-agent-commerce-kit/hack/actions/workflows/ci.yml/badge.svg)](https://github.com/hedera-agent-commerce-kit/hack/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org)
[![x402 v2](https://img.shields.io/badge/x402-v2-orange)](https://x402.org)
[![Hedera](https://img.shields.io/badge/network-Hedera-8259EF)](https://hedera.com)

</div>

---

## What is HACK.Pay?

HACK.Pay is an open-source Python library that turns any FastAPI endpoint into a paid API — using the [x402 payment protocol](https://x402.org) (v2) and [Hedera](https://hedera.com) as the settlement network.

```python
from hack_pay import paid


@app.get("/weather")
@paid("0.5 HBAR")
async def get_weather(city: str):
    return {"forecast": "sunny", "city": city}
```

A client that calls `/weather` without payment gets an HTTP `402 Payment Required` with a payment challenge. Once they pay the exact HBAR amount to your account, the request goes through automatically. No API keys, no subscriptions, no invoices.

---

## Why HACK.Pay?

| Problem | HACK.Pay solution |
|---------|-------------------|
| Per-call pricing is impossible with subscriptions | Native x402 per-request micropayments |
| AI agents can't hold credit cards or API keys | Agents pay autonomously with HBAR |
| Setting up payment infrastructure takes weeks | One decorator, two config values |
| No verifiable proof a payment happened | Every payment settles on Hedera — checkable on [HashScan](https://hashscan.io) |
| Stripe/billing requires business registration | No accounts, no invoices, no chargebacks |

---

## How it works

HACK.Pay implements the [x402 protocol](https://x402.org) exactly — no custom payment headers, no custom signatures, no custom settlement logic.

```
Client                     Your Server                  Blocky402 (Facilitator)       Hedera
  │                              │                               │                      │
  │── GET /weather ─────────────►│                               │                      │
  │◄── 402 + PAYMENT-REQUIRED ───│                               │                      │
  │                              │                               │                      │
  │  (client signs a Hedera TransferTransaction offline)         │                      │
  │                              │                               │                      │
  │── GET /weather               │                               │                      │
  │   + PAYMENT-SIGNATURE ──────►│                               │                      │
  │                              │── POST /verify ──────────────►│                      │
  │                              │◄── {valid: true} ─────────────│                      │
  │                              │── POST /settle ──────────────►│                      │
  │                              │                               │── TransferTx ────────►│
  │                              │                               │◄── SUCCESS ───────────│
  │                              │◄── {settled, tx_id} ──────────│                      │
  │◄── 200 + PAYMENT-RESPONSE ───│                               │                      │
```

1. **Challenge** — server returns 402 with `PAYMENT-REQUIRED` header (Base64-encoded `PaymentRequirements` JSON)
2. **Sign** — client builds a Hedera `TransferTransaction` (buyer → your account), signs it partially, encodes as Base64
3. **Verify + Settle** — server forwards the signed proof to [Blocky402](https://blocky402.com), which co-signs as fee payer, submits to Hedera, and waits for `SUCCESS`
4. **Grant** — server returns 200 with `PAYMENT-RESPONSE` header containing the settlement receipt

The client never needs to run a Hedera node. Your server never holds private keys. The facilitator handles all on-chain work.

---

## Key concepts

| Term | What it means |
|------|---------------|
| **x402** | Open HTTP payment protocol. A 402 response carries machine-readable payment requirements; a retry carries proof of payment. Spec at [x402.org](https://x402.org). |
| **Facilitator** | A service that co-signs, submits, and confirms Hedera transactions on behalf of clients and servers. Neither party needs a Hedera node. HACK.Pay uses [Blocky402](https://blocky402.com) by default. |
| **Resource server** | Your FastAPI app. It gates access behind payment and calls the facilitator to verify and settle. |
| **HBAR / tinybars** | Hedera's native currency. 1 HBAR = 100,000,000 tinybars. HACK.Pay always works in integer tinybars internally. |
| **CAIP-2** | Chain-agnostic network identifiers. Hedera uses `hedera:testnet` and `hedera:mainnet`. |
| **`@paid`** | The decorator that does it all — issues challenges, verifies payments, and gates your handler. |

---

## Supported networks

| Network | Facilitator URL | Status |
|---------|-----------------|--------|
| `hedera:testnet` | `https://api.testnet.blocky402.com` | v0.1 target |
| `hedera:mainnet` | `https://api.blocky402.com` | v0.1 target |

[Blocky402](https://blocky402.com) is the default facilitator — it supports both testnet and mainnet with no API key required. [x402.org/facilitator](https://x402.org/facilitator) is also supported for testnet development.

---

## Architecture at a glance

```
FastAPI Adapter  (@paid decorator, middleware)
      ↓
HACK.Pay Core    (PaymentGate — orchestrates verify/settle/idempotency/receipts)
      ↓
Provider Interface  (PaymentProvider, IdempotencyStore, ReceiptPublisher)
      ↓
x402 Adapter     (wire types, header codec — pure Python, no I/O)
      ↓
Hedera Provider  (FacilitatorClient → HTTP calls to Blocky402)
      ↓
Blocky402 / Hedera network
```

Hard rule: no layer imports from a layer above it. `hack_pay.core` has zero knowledge of FastAPI. `hack_pay.x402` has zero network I/O. See [`ARCHITECTURE.md`](ARCHITECTURE.md) for details.

---

## Project status

**Pre-release — implementation phase.**

The repository currently contains:
- Full technical design document (`.kiro/specs/hack-pay/design.md`)
- CI/CD pipeline (lint, type-check, unit/integration/security tests, testnet integration, release to PyPI)
- Project scaffold (`pyproject.toml`, `hack_pay/`, `tests/`)

Implementation of `hack_pay` is the next milestone. See the [open PR](https://github.com/hedera-agent-commerce-kit/hack/pulls) and [CHANGELOG](CHANGELOG.md).

---

## Contributing

We welcome contributors. The best place to start:

1. Read [`ARCHITECTURE.md`](ARCHITECTURE.md) — understand the layer boundaries before touching code
2. Read the design document — open the PR and navigate to `.kiro/specs/hack-pay/design.md`
3. Check [open issues](https://github.com/hedera-agent-commerce-kit/hack/issues) for `good first issue` labels

### Dev setup

```bash
# Clone and install with dev dependencies
git clone https://github.com/hedera-agent-commerce-kit/hack.git
cd hack
pip install uv
uv sync --group dev

# Run all tests (no network required)
uv run pytest tests/unit/ tests/integration/ tests/protocol/ tests/security/ tests/concurrency/

# Lint + format
uv run ruff check .
uv run ruff format .

# Type check
uv run mypy hack_pay/ --strict
```

### Testnet tests (opt-in)

```bash
# Copy .env.example → .env and fill in your testnet credentials
cp .env.example .env
# Edit .env: set HACK_PAY_RECEIVER_ACCOUNT_ID and HACK_PAY_HEDERA_NETWORK=hedera:testnet

uv run pytest tests/testnet/ -m testnet -v
```

> Testnet HBAR is free — get some at the [Hedera Developer Portal](https://portal.hedera.com).

### Before opening a PR

Every PR must pass the checklist in `.github/pull_request_template.md`. Key points:
- No secrets, private keys, or `.env` files in the diff
- Payment logic changes require security tests in `tests/security/`
- All public API changes require docstring updates

---

## License

MIT — see [LICENSE](LICENSE).

---

## Related

- [x402 protocol](https://x402.org) — the open HTTP payment standard HACK.Pay implements
- [Blocky402](https://blocky402.com) — Hedera x402 facilitator (testnet + mainnet)
- [Hedera](https://hedera.com) — the settlement network
- [Hedera Developer Portal](https://portal.hedera.com) — get testnet HBAR
- [HashScan](https://hashscan.io) — verify transactions on-chain