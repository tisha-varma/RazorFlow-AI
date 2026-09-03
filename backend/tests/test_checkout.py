import pytest


class TestCheckoutSummary:
    def _cart_with_upsell(self, client, seed_data):
        p1 = seed_data["p1"]
        p3 = seed_data["p3"]
        cart = client.post("/api/cart", json={"session_id": "sum-sess", "merchant_id": 1}).json()
        client.post(f"/api/cart/{cart['id']}/items", json={"product_id": p1.id, "quantity": 1})
        client.post(f"/api/cart/{cart['id']}/items", json={"product_id": p3.id, "quantity": 1, "is_upsell": True})
        return cart

    def test_summary_includes_policy_details(self, client, seed_data):
        cart = self._cart_with_upsell(client, seed_data)
        resp = client.get(f"/api/checkout/summary/{cart['id']}", params={"session_id": "sum-sess"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["policy_allowed"] is True
        details = data["policy_details"]
        assert details["spending_limit_paise"] == 1000000
        assert details["max_transaction"] == 500000
        assert details["approval_required"] is True
        # 449900 + 49900 = 499800; 1000000 - 499800 = 500200
        assert details["remaining_budget"] == 500200

    def test_summary_itemizes_cart_with_upsell_pairing(self, client, seed_data):
        cart = self._cart_with_upsell(client, seed_data)
        resp = client.get(f"/api/checkout/summary/{cart['id']}", params={"session_id": "sum-sess"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["upsell_total_paise"] == 49900
        upsell = next(i for i in data["items"] if i["is_upsell"])
        assert upsell["product_name"] == "Running Socks"
        assert upsell["category"] == "Accessories"
        assert upsell["reason"] == "Pairs with RunPro Sprint"
        main = next(i for i in data["items"] if not i["is_upsell"])
        assert main["reason"] is None

    def test_summary_not_found(self, client):
        resp = client.get("/api/checkout/summary/9999", params={"session_id": "sum-sess"})
        assert resp.status_code == 404

    def test_approval_summary_by_id(self, client, seed_data):
        cart = self._cart_with_upsell(client, seed_data)
        # Create the approval through the API (valid transition path)
        from backend.services.state_machine import state_machine, SessionState
        state_machine.set_state("sum-sess", SessionState.DISCOVERING)
        state_machine.set_state("sum-sess", SessionState.CART_BUILDING)
        state_machine.set_state("sum-sess", SessionState.POLICY_CHECK)
        req = client.post(
            "/api/checkout/request-approval",
            json={"cart_id": cart["id"], "session_id": "sum-sess"}
        )
        assert req.status_code == 200
        approval_id = req.json()["id"]

        resp = client.get(
            f"/api/checkout/approval/{approval_id}/summary",
            params={"session_id": "sum-sess"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["approval_id"] == approval_id
        assert data["status"] == "pending"
        assert len(data["items"]) == 2
        assert data["policy_details"]["remaining_budget"] == 500200

    def test_approval_summary_session_mismatch(self, client, seed_data):
        cart = self._cart_with_upsell(client, seed_data)
        from backend.services.state_machine import state_machine, SessionState
        state_machine.set_state("sum-sess", SessionState.DISCOVERING)
        state_machine.set_state("sum-sess", SessionState.CART_BUILDING)
        state_machine.set_state("sum-sess", SessionState.POLICY_CHECK)
        approval_id = client.post(
            "/api/checkout/request-approval",
            json={"cart_id": cart["id"], "session_id": "sum-sess"}
        ).json()["id"]

        resp = client.get(
            f"/api/checkout/approval/{approval_id}/summary",
            params={"session_id": "other-sess"}
        )
        assert resp.status_code == 403

    def test_approval_summary_not_found(self, client):
        resp = client.get(
            "/api/checkout/approval/9999/summary",
            params={"session_id": "sum-sess"}
        )
        assert resp.status_code == 404
