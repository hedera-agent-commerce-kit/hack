# Changelog

All notable changes to HACK.Pay are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial repository structure and CI/CD pipeline
- Design document for HACK.Pay v0.1 (`.kiro/specs/hack-pay/design.md`)
- `.gitignore` covering Python, Node, secrets, and Kiro IDE internals
- GitHub Actions: CI (lint, type-check, unit, integration, security scan)
- GitHub Actions: Testnet integration (manual trigger, requires secrets)
- GitHub Actions: Release (PyPI trusted publishing)
- PR template with x402/Hedera protocol compliance checklist
- `.env.example` documenting all configuration variables
- `pyproject.toml` with dependency declarations and tool configuration
- `RedisIdempotencyStore` in `hack_pay/idempotency/redis.py` — production-ready
  cross-process idempotency store backed by Redis (`hack-pay[redis]` optional extra)

## [0.1.0] — TBD

Initial release — implementation phase.
