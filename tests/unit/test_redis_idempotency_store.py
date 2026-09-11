"""tests/unit/test_redis_idempotency_store.py — RedisIdempotencyStore."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from hack_pay.idempotency.redis import RedisIdempotencyStore, _KEY_PREFIX, _serialize
from hack_pay.receipts.types import PaymentReceipt


def make_receipt(tx_id: str = "0.0.1@100.0") -> PaymentReceipt:
    return PaymentReceipt(
        transaction_id=tx_id,
        payer_account_id=None,
        receiver_account_id="0.0.12345",
        amount_tinybars=50_000_000,
        asset="0.0.0",
        network="hedera:testnet",
        settled_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        facilitator_url="https://api.testnet.blocky402.com",
    )


def make_store() -> tuple[RedisIdempotencyStore, MagicMock]:
    client = MagicMock()
    client.get = AsyncMock()
    client.set = AsyncMock()
    return RedisIdempotencyStore(client), client


@pytest.mark.asyncio
class TestRedisIdempotencyStore:
    async def test_get_returns_none_for_missing_key(self):
        store, client = make_store()
        client.get.return_value = None
        assert await store.get("missing") is None
        client.get.assert_called_once_with(f"{_KEY_PREFIX}missing")

    async def test_get_returns_deserialized_receipt(self):
        store, client = make_store()
        receipt = make_receipt()
        client.get.return_value = _serialize(receipt).encode()
        result = await store.get("key1")
        assert result == receipt

    async def test_put_calls_set_with_ttl(self):
        store, client = make_store()
        receipt = make_receipt()
        await store.put("key1", receipt, ttl_seconds=7200)
        client.set.assert_called_once_with(
            f"{_KEY_PREFIX}key1", _serialize(receipt), ex=7200
        )

    async def test_put_if_absent_stores_when_key_missing(self):
        store, client = make_store()
        receipt = make_receipt("tx-new")
        client.set.return_value = True  # NX succeeded
        result = await store.put_if_absent("key", receipt, ttl_seconds=3600)
        assert result == receipt
        client.set.assert_called_once_with(
            f"{_KEY_PREFIX}key", _serialize(receipt), nx=True, px=3600_000
        )

    async def test_put_if_absent_returns_existing_on_race(self):
        store, client = make_store()
        first = make_receipt("tx-first")
        second = make_receipt("tx-second")
        client.set.return_value = None  # NX failed — key already exists
        client.get.return_value = _serialize(first).encode()
        result = await store.put_if_absent("key", second, ttl_seconds=3600)
        assert result == first  # pre-existing receipt returned

    async def test_put_if_absent_falls_back_when_key_expires_between_set_and_get(self):
        store, client = make_store()
        receipt = make_receipt("tx-new")
        client.set.return_value = None  # NX failed
        client.get.return_value = None  # but key already expired
        result = await store.put_if_absent("key", receipt)
        assert result == receipt  # safe fallback: return the receipt we tried to store

    async def test_key_prefix_is_applied(self):
        store, client = make_store()
        client.get.return_value = None
        await store.get("abc123")
        called_key = client.get.call_args[0][0]
        assert called_key.startswith(_KEY_PREFIX)
        assert called_key == f"{_KEY_PREFIX}abc123"

    async def test_get_handles_string_response(self):
        """Redis may return str or bytes depending on decode_responses setting."""
        store, client = make_store()
        receipt = make_receipt()
        client.get.return_value = _serialize(receipt)  # str, not bytes
        result = await store.get("key")
        assert result == receipt
