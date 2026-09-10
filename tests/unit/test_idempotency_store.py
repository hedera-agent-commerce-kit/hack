"""tests/unit/test_idempotency_store.py — InMemoryIdempotencyStore."""

import asyncio
from datetime import datetime, timezone

import pytest

from hack_pay.idempotency.memory import InMemoryIdempotencyStore
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


@pytest.mark.asyncio
class TestInMemoryIdempotencyStore:
    async def test_get_returns_none_for_missing_key(self):
        store = InMemoryIdempotencyStore()
        assert await store.get("missing") is None

    async def test_put_and_get(self):
        store = InMemoryIdempotencyStore()
        receipt = make_receipt()
        await store.put("key1", receipt, ttl_seconds=3600)
        result = await store.get("key1")
        assert result == receipt

    async def test_put_if_absent_stores_first(self):
        store = InMemoryIdempotencyStore()
        receipt = make_receipt("tx-1")
        result = await store.put_if_absent("key", receipt)
        assert result == receipt
        assert await store.get("key") == receipt

    async def test_put_if_absent_returns_existing_on_race(self):
        store = InMemoryIdempotencyStore()
        first = make_receipt("tx-first")
        second = make_receipt("tx-second")
        await store.put("key", first)
        result = await store.put_if_absent("key", second)
        assert result == first  # first stored wins

    async def test_ttl_expiry(self):
        store = InMemoryIdempotencyStore()
        receipt = make_receipt()
        await store.put("key", receipt, ttl_seconds=0)
        # TTL=0 means expires immediately
        await asyncio.sleep(0.01)
        assert await store.get("key") is None

    async def test_max_entries_cap(self):
        store = InMemoryIdempotencyStore(max_entries=3)
        for i in range(3):
            await store.put(f"k{i}", make_receipt(f"tx-{i}"), ttl_seconds=3600)
        assert store.size == 3
        # Exceed cap — new entries silently dropped when no expired keys
        await store.put("k_overflow", make_receipt("tx-overflow"), ttl_seconds=3600)
        assert store.size <= 3

    async def test_concurrent_put_if_absent_exactly_one_winner(self):
        store = InMemoryIdempotencyStore()
        receipts = [make_receipt(f"tx-{i}") for i in range(10)]
        results = await asyncio.gather(*[store.put_if_absent("same_key", r) for r in receipts])
        # All results should be the same receipt (the first winner)
        assert len(set(r.transaction_id for r in results)) == 1
