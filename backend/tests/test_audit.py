import pytest


class TestAuditEndpoint:
    def _seed_trail(self, client, seed_data, session_id="audit-sess"):
        p1 = seed_data["p1"]
        cart = client.post("/api/cart", json={"session_id": session_id, "merchant_id": 1}).json()
        client.post(f"/api/cart/{cart['id']}/items", json={"product_id": p1.id, "quantity": 1})
        return cart

    def test_session_trail_ordered(self, client, seed_data):
        self._seed_trail(client, seed_data)
        resp = client.get("/api/audit", params={"session_id": "audit-sess"})
        assert resp.status_code == 200
        events = resp.json()
        assert len(events) >= 1
        types = [e["event_type"] for e in events]
        assert "POLICY_CHECK_PASSED" in types
        # Chronological order
        stamps = [(e["timestamp"], e["id"]) for e in events]
        assert stamps == sorted(stamps)
        # Shape
        first = events[0]
        for key in ("id", "event_type", "event_data", "actor", "timestamp"):
            assert key in first

        policy_event = next(e for e in events if e["event_type"] == "POLICY_CHECK_PASSED")
        assert policy_event["policy_snapshot_id"]
        assert policy_event["event_data"]["policy_snapshot_id"] == policy_event["policy_snapshot_id"]
        assert policy_event["event_data"]["policy_snapshot"]["max_transaction_paise"] == 500000

    def test_session_isolation(self, client, seed_data):
        self._seed_trail(client, seed_data, session_id="audit-a")
        self._seed_trail(client, seed_data, session_id="audit-b")
        resp = client.get("/api/audit", params={"session_id": "audit-a"})
        assert resp.status_code == 200
        assert all(e["session_id"] == "audit-a" for e in resp.json())

    def test_merchant_filter(self, client, seed_data):
        self._seed_trail(client, seed_data)
        merchant_id = seed_data["merchant"].id
        resp = client.get("/api/audit", params={"merchant_id": merchant_id})
        assert resp.status_code == 200
        assert len(resp.json()) >= 1
        assert all(e["merchant_id"] == merchant_id for e in resp.json())

    def test_requires_filter(self, client):
        resp = client.get("/api/audit")
        assert resp.status_code == 400

    def test_empty_session_returns_empty_list(self, client):
        resp = client.get("/api/audit", params={"session_id": "no-such-session"})
        assert resp.status_code == 200
        assert resp.json() == []
