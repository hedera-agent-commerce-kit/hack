## Summary

<!-- What does this PR do? One paragraph max. -->

## Type of Change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that changes existing behavior)
- [ ] Refactor (no behavior change)
- [ ] Documentation update
- [ ] CI/CD / tooling change
- [ ] Security fix

## Related Issues

<!-- Closes #123 -->

## Changes Made

<!-- Bullet list of specific changes -->
-
-

## x402 / Hedera Protocol Compliance

<!-- If this PR touches the payment path, answer these: -->

- [ ] Does not touch payment logic (skip the rest)
- [ ] `PAYMENT-REQUIRED` header format unchanged or intentionally updated
- [ ] `PAYMENT-SIGNATURE` parsing unchanged or intentionally updated
- [ ] Facilitator `/verify` and `/settle` call semantics preserved
- [ ] Amount is always validated in tinybars (never float HBAR)
- [ ] Receiver account is validated before any payment is processed
- [ ] No private keys appear anywhere in this diff

## Security Checklist

- [ ] No secrets, private keys, seed phrases, or credentials in code or test fixtures
- [ ] No sensitive values logged (amounts OK; tx IDs OK; signatures NOT OK)
- [ ] Input validation added for all new public API parameters
- [ ] New error paths do not leak internal details to the HTTP response

## Tests

- [ ] Unit tests added/updated (`tests/unit/`)
- [ ] Integration tests added/updated (`tests/integration/`)
- [ ] Security tests added if new attack surface introduced (`tests/security/`)
- [ ] All existing tests pass locally

## Documentation

- [ ] Public API changes reflected in docstrings
- [ ] CHANGELOG.md updated under `[Unreleased]`
- [ ] README / QUICKSTART updated if public API changed

## Reviewer Notes

<!-- Anything you want the reviewer to focus on or be aware of -->
