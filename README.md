# HACK.Pay

> Make any HTTP endpoint payable with a single decorator — powered by [x402](https://x402.org) and Hedera.

```python
from hack_pay import paid

@app.get("/premium-data")
@paid("0.5 HBAR")
async def premium_data():
    return {"data": "your paid content here"}
```

**Status:** Pre-release — spec phase. See `.kiro/specs/hack-pay/` for the design document.

## What This Is

HACK.Pay is an open-source Python library that adds per-request HBAR micropayments to FastAPI endpoints using the [x402 payment protocol](https://x402.org) (v2) with Hedera as the payment network.

- No custom payment protocol — pure x402 v2
- No Hedera SDK required on your server — facilitator handles all on-chain work
- Works with [Blocky402](https://blocky402.com) and [x402.org](https://x402.org/facilitator) facilitators out of the box

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) and `.kiro/specs/hack-pay/design.md`.

## Supported Networks

| Network | Facilitator | Status |
|---------|-------------|--------|
| Hedera Testnet (`hedera:testnet`) | Blocky402, x402.org | v0.1 target |
| Hedera Mainnet (`hedera:mainnet`) | Blocky402 | v0.1 target |

## Development Status

This repository is in the spec/design phase. See `.kiro/specs/hack-pay/design.md` for the full technical design.

## License

MIT
