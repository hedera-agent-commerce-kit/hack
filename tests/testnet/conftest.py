"""
tests/testnet/conftest.py — Testnet test fixtures.

These tests are opt-in only. They require real Hedera testnet credentials
set as environment variables. They are never run in CI automatically.

Run with:
    pytest tests/testnet/ -m testnet -v

Required env vars:
    HACK_PAY_TESTNET_ACCOUNT_ID     — funded testnet account
    HACK_PAY_TESTNET_PRIVATE_KEY    — ED25519 private key (hex)
    HACK_PAY_TESTNET_RECEIVER       — receiver account for test payments

Never commit real credentials. See .env.example.
"""

from __future__ import annotations

import os

import pytest


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "testnet" in str(item.fspath):
            item.add_marker(pytest.mark.testnet)


@pytest.fixture(scope="session")
def testnet_env():
    """Skip all testnet tests if credentials are not configured."""
    account_id = os.environ.get("HACK_PAY_TESTNET_ACCOUNT_ID", "")
    private_key = os.environ.get("HACK_PAY_TESTNET_PRIVATE_KEY", "")
    receiver = os.environ.get("HACK_PAY_TESTNET_RECEIVER", "")

    if not all([account_id, private_key, receiver]):
        pytest.skip(
            "Testnet credentials not configured. "
            "Set HACK_PAY_TESTNET_ACCOUNT_ID, HACK_PAY_TESTNET_PRIVATE_KEY, "
            "and HACK_PAY_TESTNET_RECEIVER to run testnet tests."
        )
    return {
        "account_id": account_id,
        "private_key": private_key,  # loaded from env, never logged
        "receiver": receiver,
    }
