"""tests/integration/test_payment_flow.py — Full 402→payment→200 flow via TestClient."""

import base64
import json


def _make_signature(payload_bytes: bytes = b"fake-hedera-transfer-tx-bytes-deterministic") -> str:
    data = {
        "x402_version": 2,
        "scheme": "exact",
        "network": "hedera:testnet",
        "payload": base64.b64encode(payload_bytes).decode(),
    }
    return base64.b64encode(json.dumps(data).encode()).decode()


class TestPaymentFlow:
    def test_unpaid_request_returns_402(self, client):
        resp = client.get("/paid-endpoint")
        assert resp.status_code == 402

    def test_402_has_payment_required_header(self, client):
        resp = client.get("/paid-endpoint")
        assert "payment-required" in {k.lower() for k in resp.headers}

    def test_payment_required_header_is_valid_base64_json(self, client):
        resp = client.get("/paid-endpoint")
        header = resp.headers.get("payment-required") or resp.headers.get("PAYMENT-REQUIRED")
        assert header is not None
        decoded = json.loads(base64.b64decode(header))
        assert decoded["scheme"] == "exact"
        assert decoded["network"] == "hedera:testnet"

    def test_valid_payment_returns_200(self, client):
        sig = _make_signature()
        resp = client.get("/paid-endpoint", headers={"PAYMENT-SIGNATURE": sig})
        assert resp.status_code == 200

    def test_200_response_has_payment_response_header(self, client):
        sig = _make_signature()
        resp = client.get("/paid-endpoint", headers={"PAYMENT-SIGNATURE": sig})
        header_names = {k.lower() for k in resp.headers}
        assert "payment-response" in header_names

    def test_free_endpoint_always_200(self, client):
        resp = client.get("/free-endpoint")
        assert resp.status_code == 200

    def test_malformed_signature_returns_402(self, client):
        resp = client.get("/paid-endpoint", headers={"PAYMENT-SIGNATURE": "not-valid-base64!!!"})
        assert resp.status_code == 402

    def test_v1_header_returns_402_with_clear_message(self, client):
        resp = client.get("/paid-endpoint", headers={"X-PAYMENT": "old-v1-payload"})
        assert resp.status_code == 402

    def test_replay_same_signature_returns_200(self, client):
        sig = _make_signature(b"unique-replay-bytes")
        r1 = client.get("/paid-endpoint", headers={"PAYMENT-SIGNATURE": sig})
        r2 = client.get("/paid-endpoint", headers={"PAYMENT-SIGNATURE": sig})
        assert r1.status_code == 200
        assert r2.status_code == 200

    def test_response_body_contains_expected_data(self, client):
        sig = _make_signature(b"data-check-bytes")
        resp = client.get("/paid-endpoint", headers={"PAYMENT-SIGNATURE": sig})
        assert resp.json()["data"] == "secret content"
