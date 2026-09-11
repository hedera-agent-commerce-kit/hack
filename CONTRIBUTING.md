# Contributing to HACK.Pay

Thank you for your interest in contributing. This guide covers everything you need to get a
working development environment, run the test suite, and submit a pull request.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Fork and clone](#fork-and-clone)
3. [Dev environment setup](#dev-environment-setup)
4. [Running tests](#running-tests)
5. [Linting and type checking](#linting-and-type-checking)
6. [Code style rules](#code-style-rules)
7. [Import layer rules](#import-layer-rules)
8. [Pull request process](#pull-request-process)
9. [Running the example app](#running-the-example-app)
10. [Getting help](#getting-help)

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.10 – 3.14 | [python.org](https://www.python.org/downloads/) |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` (macOS/Linux) or [docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/) |
| git | any recent | [git-scm.com](https://git-scm.com/) |

Verify your setup:

```bash
python --version   # should be 3.10.x – 3.14.x
uv --version
git --version
```

---

## Fork and clone

1. Fork the repository on GitHub: <https://github.com/hedera-agent-commerce-kit/hack>
2. Clone your fork:

```bash
git clone https://github.com/<your-username>/hack.git
cd hack
```

3. Add the upstream remote so you can pull in future changes:

```bash
git remote add upstream https://github.com/hedera-agent-commerce-kit/hack.git
```

---

## Dev environment setup

Install all development dependencies (including the `fastapi` extras, `pytest`, `mypy`,
`ruff`, `bandit`, `hypothesis`, and `import-linter`) with a single command:

```bash
uv sync --group dev
```

`uv` creates a `.venv` automatically and installs everything into it. You do not need to
activate it manually — every `uv run` command below uses it automatically.

Copy the example environment file and fill in your values (testnet credentials are only
required for testnet tests):

```bash
cp .env.example .env
```

---

## Running tests

### Run the full test suite

```bash
uv run pytest
```

### Run with coverage report

```bash
uv run pytest --cov=hack_pay --cov-report=term-missing
```

### Skip testnet tests (no Hedera credentials needed)

```bash
uv run pytest -m "not testnet"
```

### Run a single file

```bash
uv run pytest tests/unit/test_properties.py -v
```

### Run a specific test by name

```bash
uv run pytest -k "test_gate_returns_payment_required" -v
```

### Test layout

| Directory | What it covers |
|-----------|---------------|
| `tests/unit/` | Pure unit tests, no I/O |
| `tests/integration/` | Gate and decorator behaviour with mocked providers |
| `tests/concurrency/` | Idempotency store under concurrent access |
| `tests/protocol/` | x402 wire format correctness |
| `tests/security/` | Auth and replay-protection paths |
| `tests/testnet/` | Real Hedera testnet calls (requires `.env` credentials, mark: `testnet`) |

---

## Linting and type checking

Run all checks before opening a PR. Every command below must exit cleanly.

### Check for lint errors

```bash
uv run ruff check .
```

### Auto-fix safe lint violations

```bash
uv run ruff check . --fix
```

### Format code

```bash
uv run ruff format .
```

### Type-check the library (strict mode)

```bash
uv run mypy hack_pay/ --strict
```

### Security scan

```bash
uv run bandit -r hack_pay/
```

### Dependency vulnerability audit

```bash
uv run pip-audit
```

### Check import-layer boundaries

```bash
uv run lint-imports
```

---

## Code style rules

**Formatter:** `ruff format` — do not run `black` or `autopep8`.

**Line length:** 100 characters.

**Enabled rule sets:**

| Code | Rule set |
|------|----------|
| `E`, `F`, `W` | pycodestyle / pyflakes (errors, warnings) |
| `I` | isort (import ordering) |
| `N` | PEP 8 naming conventions |
| `UP` | pyupgrade (modern Python idioms) |
| `B` | flake8-bugbear (common bugs) |
| `S` | flake8-bandit (security) |
| `A` | flake8-builtins (shadowing built-ins) |

`S101` (use of `assert`) is allowed in test files.

**Type annotations:** all public functions and methods must be fully annotated. `mypy --strict`
must pass with no errors or `# type: ignore` comments unless absolutely unavoidable (in which
case add a comment explaining why).

**Docstrings:** not required for private helpers, but public-facing classes and functions
should have a one-line summary.

---

## Import layer rules

The codebase enforces a strict dependency hierarchy. Violations are caught by `lint-imports`.

```
foundation modules  ← imported by —  core/providers  ← imported by —  adapters
```

Specifically:

- `hack_pay.core` **must not** import from `hack_pay.adapters`, `fastapi`, or `starlette`.
- `hack_pay.x402` **must not** import from `httpx`, `hack_pay.adapters`, or
  `hack_pay.providers.hedera`.

If you need to share behaviour across layers, place it in the layer below the lowest importer
(typically `hack_pay.core`) or use an abstract interface/protocol.

---

## Pull request process

### Branch naming

Use a short, descriptive branch name:

```
feature/<what-you-built>
fix/<what-you-fixed>
docs/<what-you-documented>
chore/<what-you-cleaned-up>
```

Example: `fix/encode-payment-response-by-alias`

### Commit conventions

- Write commits in the imperative mood: "Add test for settlement failure" not "Added…"
- Keep the subject line under 72 characters.
- Reference the relevant issue number if one exists: `Fixes #42`

### Pre-PR checklist

Before requesting review, confirm all of the following:

- [ ] `uv run pytest -m "not testnet"` passes with no failures
- [ ] `uv run mypy hack_pay/ --strict` reports zero errors
- [ ] `uv run ruff check .` reports zero violations
- [ ] `uv run ruff format . --check` reports no files would change
- [ ] `uv run lint-imports` passes
- [ ] New functionality has corresponding unit tests
- [ ] Coverage has not regressed (check with `--cov=hack_pay --cov-report=term-missing`)
- [ ] `CHANGELOG.md` is updated if your change is user-visible

### Review process

1. Open a PR against the `main` branch with a clear title and description.
2. CI runs automatically — all checks must go green before review begins.
3. Address reviewer comments with new commits; do not force-push after review has started.
4. Once approved and CI is green, a maintainer will merge using squash merge.

---

## Running the example app

A complete FastAPI example app lives in `examples/basic_fastapi/`. Follow its README for
step-by-step instructions on starting a local server with a mock payment provider:

```bash
cat examples/basic_fastapi/README.md
```

---

## Getting help

- **Bug reports and feature requests:** open an issue at
  <https://github.com/hedera-agent-commerce-kit/hack/issues>
- **Questions:** start a discussion or comment on an existing issue
- **Security vulnerabilities:** see [SECURITY.md](./SECURITY.md) for the responsible
  disclosure process — do **not** open a public issue for security bugs
