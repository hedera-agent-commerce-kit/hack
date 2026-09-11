# Security Policy — HACK.Pay

This document covers the threat model for `hack-pay`, responsible disclosure instructions, and an explicit list of threats that are **outside** the library's scope.

---

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.0   | Yes — current release |
| < 0.1.0 | No — pre-release commits receive no security fixes |

---

## Threat Model Summary

`hack-pay` is a Python library that gates HTTP endpoints behind x402 micropayments settled on Hedera. It does not serve network traffic directly; it sits inside a FastAPI application operated by the developer. The attack surface is therefore the interaction between an HTTP client submitting payment proofs and the library's validation, settlement, and response logic.

The library defends against the following threat categories.

### Input Validation

Payment amounts are derived server-side from `PaymentConfig.amount_tinybars` and encoded into the `PAYMENT-REQUIRED` challenge. The `PaymentRequirements` model rejects zero, negative, and non-integer amounts at construction time via Pydantic validation. No field in the inbound `PAYMENT-SIGNATURE` header is trusted as an authoritative amount — the header is validated against the server's own requirements, not the reverse.

### Replay Attacks

Every settled payment is stored in an `IdempotencyStore` keyed on a deterministic hash of the payment proof. Replaying the same `PAYMENT-SIGNATURE` any number of times triggers a single settlement call; all subsequent requests return the cached receipt. A per-key `asyncio.Lock` with a double-check pattern prevents the TOCTOU race under concurrent requests carrying the same proof.

### SSRF (Server-Side Request Forgery)

`HederaProviderConfig` validates the facilitator URL at application startup. Plain HTTP URLs are rejected. Loopback addresses (`localhost`, `127.0.0.1`, `::1`) and private-subnet addresses (RFC 1918: `10.x`, `172.16–31.x`, `192.168.x`) are rejected. Only public HTTPS URLs are accepted. This prevents an operator misconfiguration from routing settlement calls to internal infrastructure.

### Information Disclosure in Error Responses

HTTP error responses produced by `error_to_response()` never contain Python tracebacks, stack traces, raw exception messages, or internal diagnostic detail. Each error type maps to a fixed safe `message` string and a machine-readable `code`. The HTTP status codes are:

| Error category | Status |
|----------------|--------|
| Payment errors (invalid, insufficient, malformed, mismatch, expired) | 402 |
| Oversized header | 400 |
| Facilitator errors | 502 |
| Facilitator timeout | 504 |
| Durable receipt unavailable | 503 |

### Header Denial-of-Service

`decode_payment_signature()` measures the raw header length before any parsing. Headers exceeding 65,536 bytes (64 KiB) raise `OversizedPaymentHeaderError` immediately and are never parsed. This prevents memory exhaustion from deliberately oversized Base64 payloads.

### Log Field Leakage

`PaymentEventContext` — the dataclass passed to every `PaymentEventHook` — deliberately excludes payment payload bytes, raw signature strings, and private key material. `LoggingPaymentEventHook` emits only event type, endpoint, and transaction ID. Transaction IDs (e.g., `0.0.12345@1725000000.000000000`) are safe to log; raw proof bytes are not.

### Recipient Integrity

After `settle()` returns, `validate_settlement_recipient()` compares the settled payer against `requirements.pay_to`. A mismatch raises `RecipientMismatchError`, preventing a compromised facilitator from crediting a different account without detection.

### Payment Expiry Enforcement

`validate_payload_matches_requirements()` checks the `valid_until` timestamp in the decoded payload. Expired proofs raise `ExpiredPaymentError` before any network call is made to the facilitator.

### Network and Asset Integrity

The same validation step checks that the payload's `network` and `asset` fields match the server's configured values. Mismatches raise `NetworkMismatchError` or `AssetMismatchError` respectively, preventing cross-network or cross-asset payment substitution.

---

## What HACK.Pay Does NOT Defend Against

The following threats are explicitly **outside** the library's scope. Operators must address them independently.

- **DDoS and rate limiting.** The library has no built-in rate limiting or request throttling. A flood of requests — paid or unpaid — will exhaust server resources. Use a reverse proxy (nginx, Caddy), a WAF, or FastAPI middleware such as `slowapi` to enforce per-IP or per-client limits.

- **Wallet key management and custody.** `hack-pay` does not manage private keys. The Hedera operator account used by the facilitator is outside the library's control. Operators are responsible for secure key storage, rotation, and HSM or secrets-manager integration.

- **Facilitator compromise.** The library trusts the configured Blocky402 or x402.org facilitator to verify and settle payments honestly. If the facilitator is compromised or returns fraudulent settlement proofs, the library will accept them. Use a reputable, monitored facilitator and consider running your own if the trust assumption is unacceptable for your use case.

- **TLS and transport security.** `hack-pay` does not terminate TLS. The SSRF guard applies only to outbound facilitator connections. Inbound HTTPS termination is the operator's responsibility (e.g., via a reverse proxy or a cloud load balancer).

- **Application-layer authorization.** Payment verification is not identity verification. `hack-pay` does not restrict which Hedera accounts are allowed to pay, impose per-user spending limits, or perform KYC/AML checks. Any client that can produce a valid payment proof for the required amount is granted access. Layer additional authorization logic in your route handlers if needed.

- **Business logic fraud.** Paying the configured amount grants access unconditionally. The library does not validate whether a given payer should have access for business reasons, whether the endpoint is appropriate for a given client, or whether downstream content is correct. These checks belong in application code.

- **Hedera network-level attacks.** Consensus attacks, Hedera node compromise, and Mirror Node downtime are outside the library's control. `hack-pay` inherits the security properties of the Hedera network and the operator's chosen facilitator.

- **Memory store persistence and cross-process replay protection.** `InMemoryIdempotencyStore` is non-persistent and single-process. Replay protection resets on every process restart. Operators requiring cross-restart or cross-process (multi-worker) replay protection must implement a durable `IdempotencyStore` backend (e.g., Redis, PostgreSQL). See the `IdempotencyStore` ABC in `hack_pay/idempotency/base.py`.

- **Supply chain attacks.** `hack-pay` does not audit its transitive dependencies (pydantic, httpx, fastapi). Pin all dependencies using `uv lock` or pip hash-checking, audit with `pip-audit`, and subscribe to security advisories for these packages independently.

- **Secrets in environment variables.** The library reads configuration from environment variables but does not enforce secret rotation, audit access to those variables, or detect leaked credentials. Use a secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.) and rotate credentials regularly.

---

## Responsible Disclosure

If you discover a security vulnerability in `hack-pay`, please report it privately so that a fix can be prepared before public disclosure.

**Report a vulnerability here:**
[https://github.com/hedera-agent-commerce-kit/hack/security/advisories/new](https://github.com/hedera-agent-commerce-kit/hack/security/advisories/new)

GitHub Security Advisories allow you to submit a report confidentially. The repository maintainers will be notified and can collaborate with you in a private thread before any public disclosure.

### What to include

A useful report includes:

- A description of the vulnerability and the affected component
- Steps to reproduce, including any proof-of-concept code
- The potential impact and attack conditions
- The version of `hack-pay` you tested against

### Response expectations

- **Acknowledgement:** within 5 business days of submission
- **Triage and initial assessment:** within 10 business days
- **Patch for critical or high severity issues:** within 90 days of confirmation
- **Coordinated disclosure:** fixes are released before any public writeup; the advisory is published together with the patched release

We follow a coordinated disclosure model. Please do not open a public issue for a security vulnerability before a fix has been released.
