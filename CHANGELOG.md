# Changelog

All notable changes to HACK.Pay are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

---

## [0.1.0] — TBD

### Added

#### x402 gate (`hack_pay/core/gate.py`)
- `PaymentGate` — central async payment gate that orchestrates the full
  challenge → verify → settle → grant lifecycle.
- Issues HTTP 402 challenges (returns `ChallengeResult`) when no
  `PAYMENT-SIGNATURE` header is present.
- Decodes and validates the `PAYMENT-SIGNATURE` header before forwarding to
  the provider, with a 64 KB size guard against decompression-bomb attacks.
- Validates payload fields against server-issued requirements (network, scheme)
  before any network call.
- Delegates `verify()` and `settle()` to the injected `PaymentProvider`.
- In-flight deduplication: concurrent requests carrying the same idempotency
  key are coalesced — only one verify+settle call reaches the facilitator.
- Returns `GrantedResult` on success, `ErrorResult` on any payment or
  facilitator failure, with every error mapped to a machine-readable `code`.
- Calls `ReceiptPublisher.publish()` after settlement; blocks the request when
  `require_durable_receipt=True` and the publisher is unavailable.
- Emits structured `PaymentEvent` lifecycle events to registered hooks at
  each stage (challenge, verify start/success/failure, settle start/
  success/failure, receipt published, idempotency hit, replay detected).

#### `@paid` decorator (`hack_pay/adapters/fastapi/decorator.py`)
- `paid(amount)` — FastAPI endpoint decorator that gates any handler behind
  an x402 payment wall.
- Accepts a concise string amount (`"0.5 HBAR"`) or a full `PaymentConfig`
  object for advanced configuration.
- Parses HBAR strings to exact tinybar integers using `Decimal` arithmetic
  (never `float`) to avoid rounding errors.
- Automatically extracts the `fastapi.Request` argument from the decorated
  handler's positional or keyword arguments; raises `ConfigurationError` at
  startup if no `Request` parameter is present.
- Translates `GateResult` variants to HTTP responses: 402 with
  `PAYMENT-REQUIRED` header on challenge, 200 with `PAYMENT-RESPONSE` header
  on grant, and appropriate 4xx/5xx JSON error bodies on failure.

#### `HackPay` app wrapper (`hack_pay/adapters/fastapi/app.py`)
- `HackPay` — FastAPI lifecycle manager; call `await hack.startup(app)` in
  the lifespan context to initialise the provider, then `await hack.shutdown()`
  to close the HTTP connection pool cleanly.
- `HackPayConfig` — top-level configuration dataclass accepting a
  `PaymentProvider`, optional `IdempotencyStore`, optional
  `ReceiptPublisher`, optional list of `PaymentEventHook` instances, and an
  idempotency TTL.
- Validates at startup that the facilitator advertises the configured
  network + `scheme=exact` combination; raises `FacilitatorNetworkNotSupportedError`
  if the check fails rather than silently continuing.

#### Hedera payment provider (`hack_pay/providers/hedera/`)
- `HederaPaymentProvider` — `PaymentProvider` implementation that delegates
  all on-chain work to a public x402 facilitator; the resource server holds
  no Hedera private key.
- Fetches `GET /supported` at startup to cache the facilitator's `feePayer`
  account ID and injects it into every `PaymentRequirements.extra.feePayer`
  field (required by the Hedera exact scheme).
- `FacilitatorClient` — shared `httpx.AsyncClient` (connection pool, 20
  connections, 10 keep-alive) with configurable timeout, retry count, and
  exponential back-off for transient 5xx / timeout errors.
- `HederaProviderConfig` — frozen dataclass with startup-time validation:
  Hedera `shard.realm.num` account ID format, HTTPS-only facilitator URL,
  SSRF guard (rejects private/loopback addresses), and CAIP-2 network
  constraint (`hedera:testnet` / `hedera:mainnet`).
- `parse_hbar_string()` / `format_tinybars()` — `Decimal`-based HBAR ↔
  tinybar conversion with exact precision up to 8 decimal places.
- `load_hedera_config_from_env()` — builds `HederaProviderConfig` from
  `HACK_PAY_RECEIVER_ACCOUNT_ID`, `HACK_PAY_HEDERA_NETWORK`, and
  `HACK_PAY_FACILITATOR_URL` environment variables.

#### x402 codec (`hack_pay/x402/codec.py`)
- `encode_payment_required()` — serialises `PaymentRequirements` to
  Base64(UTF-8 JSON) for the `PAYMENT-REQUIRED` response header.
- `decode_payment_signature()` — decodes `PAYMENT-SIGNATURE` header with
  size guard, Base64 validation, JSON parsing, version check (rejects x402
  v1 `X-PAYMENT` header with a clear error), and Pydantic model validation.
- `encode_payment_response()` — serialises `SettlementResponse` to
  Base64(UTF-8 JSON) for the `PAYMENT-RESPONSE` response header.
- `extract_payment_signature_header()` — case-insensitive header lookup that
  actively rejects x402 v1 `X-PAYMENT` headers rather than silently ignoring
  them.

#### x402 wire types (`hack_pay/x402/types.py`)
- Pydantic models for the x402 v2 wire protocol: `PaymentRequirements`,
  `PaymentPayload`, `SettlementResponse`, and the Hedera-specific
  `FacilitatorSupportedResponse` / `FacilitatorVerifyResponse` shapes.
- All models use `by_alias=True` serialisation so field names match the
  camelCase wire format (e.g. `payTo`, `x402Version`, `feePayer`).

#### x402 structural validation (`hack_pay/x402/validation.py`)
- `validate_payload_matches_requirements()` — pre-provider guard that raises
  `NetworkMismatchError` or `AssetMismatchError` when the client's payment
  proof targets the wrong network or scheme, without making any network call.
- `validate_settlement_recipient()` — post-settlement guard that raises
  `RecipientMismatchError` when the on-chain recipient does not match the
  configured `receiver_account_id` (skipped when the facilitator does not
  return the `payTo` field).

#### Idempotency store (`hack_pay/idempotency/`)
- `IdempotencyStore` — abstract base class (`get`, `put`, `put_if_absent`)
  for pluggable idempotency backends.
- `InMemoryIdempotencyStore` — `asyncio.Lock`-backed in-memory store with
  configurable `max_entries` capacity and per-entry TTL (monotonic clock).
  Evicts expired entries before capacity checks. Thread-safe for single-process
  deployments. Not suitable for multi-process production (Redis/PostgreSQL
  adapters can be plugged in via `IdempotencyStore`).
- `derive_idempotency_key()` — SHA-256 digest of the raw `TransferTransaction`
  bytes extracted from `PaymentPayload.payload`; stable across retries and
  independent of header encoding variations.

#### Receipt publisher abstraction (`hack_pay/receipts/`)
- `ReceiptPublisher` — abstract base class (`publish`, `is_available`) for
  durable receipt recording backends (e.g. HCS, database).
- `NoopReceiptPublisher` — default no-op implementation for deployments that
  do not require durable receipts.
- `PaymentReceipt` — immutable Pydantic model capturing `transaction_id`,
  `amount_tinybars`, `network`, `pay_to`, `payer`, `endpoint`, and
  `settled_at` timestamp.

#### Error hierarchy (`hack_pay/errors.py`)
- `HackPayError` — base class with machine-readable `code` string.
- `ConfigurationError` — raised at startup for missing or invalid config.
- `PaymentError` (base) and subclasses: `MalformedPaymentError`,
  `UnsupportedProtocolVersionError`, `InvalidPaymentError`,
  `InsufficientPaymentError`, `RecipientMismatchError`, `AssetMismatchError`,
  `NetworkMismatchError`, `ExpiredPaymentError`, `OversizedPaymentHeaderError`.
- `FacilitatorError` (base) and subclasses: `FacilitatorUnavailableError`,
  `FacilitatorTimeoutError`, `FacilitatorNetworkNotSupportedError`,
  `FacilitatorInvalidResponseError`.
- `ReceiptError` (base) and subclass: `DurableReceiptUnavailableError`.
- All errors carry a distinct `code` string for structured logging and
  programmatic handling; HTTP responses expose only a safe top-level message.
- FastAPI error-to-response mapping (`adapters/fastapi/errors.py`) converts
  every `HackPayError` subclass to the correct HTTP status code.

#### Observability (`hack_pay/observability/`)
- `PaymentEventHook` — abstract interface for payment lifecycle observers.
- `PaymentEvent` enum — 10 lifecycle events: `challenge_issued`,
  `verify_start`, `verify_success`, `verify_failure`, `settle_start`,
  `settle_success`, `settle_failure`, `receipt_published`,
  `idempotency_hit`, `replay_detected`.
- `PaymentEventContext` — frozen dataclass; deliberately excludes payment
  payload bytes, private keys, and full signatures to prevent log leakage.
- `LoggingPaymentEventHook` — emits one structured JSON log line per event
  to the `hack_pay.payments` logger; uses `WARNING` for failure events and
  `INFO` for all others.

#### Test suite (`tests/`)
- **Unit tests** (`tests/unit/`): amount parsing (HBAR string → tinybars,
  edge cases), x402 codec (encode/decode round-trips, size guard, version
  rejection), config validation (account ID format, URL SSRF guard, network
  constraint), error hierarchy (code strings, repr), gate challenge path,
  gate error paths, gate granted path, idempotency store (TTL, capacity,
  concurrent `put_if_absent`).
- **Integration tests** (`tests/integration/`): full payment flow
  (challenge → pay → grant) with mocked provider, facilitator timeout
  handling.
- **Protocol conformance tests** (`tests/protocol/`): `PAYMENT-REQUIRED`
  header encoding and round-trip decoding against the x402 v2 wire format.
- **Security tests** (`tests/security/`): amount manipulation, exception
  message leakage, log field leakage, oversized header rejection, replay
  attack prevention, SSRF guard on facilitator URL.
- **Concurrency tests** (`tests/concurrency/`): duplicate in-flight payment
  race — concurrent requests with the same key are coalesced to a single
  verify+settle call.

#### Infrastructure and packaging
- `pyproject.toml` — package metadata, `hack-pay[fastapi]` optional extra,
  `ruff` and `mypy --strict` configuration, `pytest` configuration.
- `py.typed` marker (PEP 561) — downstream `mypy` consumers receive type
  information from the installed wheel.
- `__version__ = "0.1.0"` exported from package root.
- `.env.example` — documents all environment variables
  (`HACK_PAY_RECEIVER_ACCOUNT_ID`, `HACK_PAY_HEDERA_NETWORK`,
  `HACK_PAY_FACILITATOR_URL`).
- GitHub Actions workflows: CI (lint, type-check, unit, integration, security
  scan), testnet integration (manual trigger), release (PyPI trusted
  publishing).

[0.1.0]: https://github.com/hedera-agent-commerce-kit/hack-pay/releases/tag/v0.1.0
