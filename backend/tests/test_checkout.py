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


class TestApprovalToken:
    def _pending_approval(self, client, seed_data, session_id):
        from backend.services.state_machine import state_machine, SessionState
        p1 = seed_data["p1"]
        cart = client.post("/api/cart", json={"session_id": session_id, "merchant_id": 1}).json()
        client.post(f"/api/cart/{cart['id']}/items", json={"product_id": p1.id, "quantity": 1})
        state_machine.set_state(session_id, SessionState.DISCOVERING)
        state_machine.set_state(session_id, SessionState.CART_BUILDING)
        state_machine.set_state(session_id, SessionState.POLICY_CHECK)
        return client.post(
            "/api/checkout/request-approval",
            json={"cart_id": cart["id"], "session_id": session_id}
        ).json()

    def test_token_issued_at_creation(self, client, seed_data):
        appr = self._pending_approval(client, seed_data, "tok-sess-1")
        assert appr["approval_token"] and len(appr["approval_token"]) >= 32

    def test_approve_missing_token_rejected(self, client, seed_data):
        appr = self._pending_approval(client, seed_data, "tok-sess-2")
        resp = client.post(
            f"/api/checkout/approve/{appr['id']}", json={"session_id": "tok-sess-2"}
        )
        assert resp.status_code == 422  # required field absent

    def test_approve_wrong_token_rejected(self, client, seed_data):
        appr = self._pending_approval(client, seed_data, "tok-sess-3")
        resp = client.post(
            f"/api/checkout/approve/{appr['id']}",
            json={"session_id": "tok-sess-3", "approval_token": "wrong-token"}
        )
        assert resp.status_code == 403

    def test_token_single_use_no_replay(self, client, seed_data, db_session):
        from backend.models.approval import Approval
        appr = self._pending_approval(client, seed_data, "tok-sess-4")
        body = {"session_id": "tok-sess-4", "approval_token": appr["approval_token"]}
        first = client.post(f"/api/checkout/approve/{appr['id']}", json=body)
        assert first.status_code == 200
        # Token consumed: replay fails even though the id/session are right.
        second = client.post(f"/api/checkout/approve/{appr['id']}", json=body)
        assert second.status_code in (400, 403)
        db_session.expire_all()
        assert db_session.query(Approval).filter(
            Approval.id == appr["id"]).one().approval_token is None

    def test_reject_requires_token(self, client, seed_data):
        appr = self._pending_approval(client, seed_data, "tok-sess-5")
        bad = client.post(
            f"/api/checkout/reject/{appr['id']}",
            json={"session_id": "tok-sess-5", "approval_token": "nope"}
        )
        assert bad.status_code == 403
        good = client.post(
            f"/api/checkout/reject/{appr['id']}",
            json={"session_id": "tok-sess-5", "approval_token": appr["approval_token"]}
        )
        assert good.status_code == 200
        assert good.json()["status"] == "rejected"


class TestRestartRecovery:
    def _pending_approval(self, client, seed_data, session_id):
        from backend.services.state_machine import state_machine, SessionState
        p1 = seed_data["p1"]
        cart = client.post("/api/cart", json={"session_id": session_id, "merchant_id": 1}).json()
        client.post(f"/api/cart/{cart['id']}/items", json={"product_id": p1.id, "quantity": 1})
        state_machine.set_state(session_id, SessionState.DISCOVERING)
        state_machine.set_state(session_id, SessionState.CART_BUILDING)
        state_machine.set_state(session_id, SessionState.POLICY_CHECK)
        return client.post(
            "/api/checkout/request-approval",
            json={"cart_id": cart["id"], "session_id": session_id}
        ).json()

    def _simulate_restart(self, session_id):
        from backend.services.state_machine import state_machine, SessionState
        state_machine._sessions.pop(session_id, None)
        assert state_machine.get_state(session_id) == SessionState.IDLE

    def test_approve_after_restart_recovers(self, client, seed_data):
        from backend.services.state_machine import state_machine, SessionState
        appr = self._pending_approval(client, seed_data, "restart-sess-1")
        self._simulate_restart("restart-sess-1")

        resp = client.post(f"/api/checkout/approve/{appr['id']}", json={
            "session_id": "restart-sess-1", "approval_token": appr["approval_token"]})
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"
        assert state_machine.get_state("restart-sess-1") == SessionState.PAYMENT_PENDING

    def test_reject_after_restart_recovers(self, client, seed_data):
        from backend.services.state_machine import state_machine, SessionState
        appr = self._pending_approval(client, seed_data, "restart-sess-2")
        self._simulate_restart("restart-sess-2")

        resp = client.post(f"/api/checkout/reject/{appr['id']}", json={
            "session_id": "restart-sess-2", "approval_token": appr["approval_token"]})
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

    def test_no_recovery_without_live_rows(self, db_session):
        from backend.services.checkout_service import CheckoutService
        from backend.services.state_machine import state_machine, SessionState
        assert CheckoutService.recover_session_state(db_session, "restart-empty") is None
        assert state_machine.get_state("restart-empty") == SessionState.IDLE


class TestPolicyChangeMidSession:
    def _approved_setup(self, client, seed_data, session_id):
        from backend.services.state_machine import state_machine, SessionState
        p1 = seed_data["p1"]
        cart = client.post("/api/cart", json={"session_id": session_id, "merchant_id": 1}).json()
        client.post(f"/api/cart/{cart['id']}/items", json={"product_id": p1.id, "quantity": 1})
        state_machine.set_state(session_id, SessionState.DISCOVERING)
        state_machine.set_state(session_id, SessionState.CART_BUILDING)
        state_machine.set_state(session_id, SessionState.POLICY_CHECK)
        return client.post(
            "/api/checkout/request-approval",
            json={"cart_id": cart["id"], "session_id": session_id}
        ).json()

    def test_approve_refused_after_tightening(self, client, seed_data, db_session):
        from backend.models.policy import CommercePolicy
        from backend.models.approval import Approval

        appr = self._approved_setup(client, seed_data, "tight-sess-1")
        # Merchant tightens the limit below the approved amount mid-session.
        policy = db_session.query(CommercePolicy).first()
        policy.max_transaction_amount_paise = 300000
        db_session.commit()

        resp = client.post(f"/api/checkout/approve/{appr['id']}", json={
            "session_id": "tight-sess-1", "approval_token": appr["approval_token"]})
        assert resp.status_code == 400
        assert "Policy no longer allows" in resp.json()["detail"]

        db_session.expire_all()
        assert db_session.query(Approval).filter(
            Approval.id == appr["id"]).one().status == "pending"

    def test_approve_allowed_when_policy_unchanged(self, client, seed_data):
        appr = self._approved_setup(client, seed_data, "tight-sess-2")
        resp = client.post(f"/api/checkout/approve/{appr['id']}", json={
            "session_id": "tight-sess-2", "approval_token": appr["approval_token"]})
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"


class TestStaleApproval:
    def _cart_with_shoe(self, db_session, seed_data, session_id):
        from backend.services.cart_service import CartService
        cart = CartService.create_cart(db_session, session_id, 1)
        CartService.add_item(db_session, cart.id, seed_data["p1"].id, quantity=1)
        return cart

    def test_unchanged_cart_reuses_approval(self, db_session, seed_data):
        from backend.services.checkout_service import CheckoutService
        cart = self._cart_with_shoe(db_session, seed_data, "stale-sess-1")
        first = CheckoutService.create_approval(db_session, "stale-sess-1", cart.id)
        second = CheckoutService.create_approval(db_session, "stale-sess-1", cart.id)
        assert second["reused"] is True
        assert second["approval"].id == first["approval"].id

    def test_changed_cart_expires_old_and_creates_new(self, db_session, seed_data):
        from backend.services.cart_service import CartService
        from backend.services.checkout_service import CheckoutService
        from backend.models.approval import Approval
        from backend.models.audit import AuditEvent

        cart = self._cart_with_shoe(db_session, seed_data, "stale-sess-2")
        first = CheckoutService.create_approval(db_session, "stale-sess-2", cart.id)
        assert first["approval"].requested_amount_paise == 449900

        # Mutate the cart after approval (e.g. upsell added).
        CartService.add_item(db_session, cart.id, seed_data["p3"].id, quantity=1)
        second = CheckoutService.create_approval(db_session, "stale-sess-2", cart.id)

        assert second.get("reused", False) is False
        assert second["approval"].id != first["approval"].id
        assert second["approval"].requested_amount_paise == 449900 + 49900

        db_session.expire_all()
        old = db_session.query(Approval).filter(Approval.id == first["approval"].id).one()
        assert old.status == "expired"
        expired_evt = db_session.query(AuditEvent).filter(
            AuditEvent.event_type == "PAYMENT_APPROVAL_EXPIRED",
            AuditEvent.related_entity_id == old.id
        ).one()
        assert expired_evt.event_data["old_amount_paise"] == 449900
        assert expired_evt.event_data["new_amount_paise"] == 499800
        # Exactly one pending approval survives.
        pending = db_session.query(Approval).filter(
            Approval.session_id == "stale-sess-2",
            Approval.status == "pending"
        ).all()
        assert [a.id for a in pending] == [second["approval"].id]

    def test_create_order_rejects_changed_cart(self, client, seed_data):
        # Approve, then mutate the cart, then attempt payment: must refuse.
        p1 = seed_data["p1"]
        p3 = seed_data["p3"]
        cart = client.post("/api/cart", json={"session_id": "stale-sess-3", "merchant_id": 1}).json()
        client.post(f"/api/cart/{cart['id']}/items", json={"product_id": p1.id, "quantity": 1})
        from backend.services.state_machine import state_machine, SessionState
        state_machine.set_state("stale-sess-3", SessionState.DISCOVERING)
        state_machine.set_state("stale-sess-3", SessionState.CART_BUILDING)
        state_machine.set_state("stale-sess-3", SessionState.POLICY_CHECK)
        appr = client.post(
            "/api/checkout/request-approval",
            json={"cart_id": cart["id"], "session_id": "stale-sess-3"}
        ).json()
        client.post(f"/api/checkout/approve/{appr['id']}", json={
            "session_id": "stale-sess-3", "approval_token": appr["approval_token"]})
        # Cart changes AFTER approval.
        client.post(f"/api/cart/{cart['id']}/items", json={"product_id": p3.id, "quantity": 1})

        resp = client.post(
            f"/api/payment/create-order/{appr['id']}", json={"session_id": "stale-sess-3"}
        )
        assert resp.status_code == 409
        assert "changed since approval" in resp.json()["detail"]

    def test_create_order_rejects_policy_drift(self, client, seed_data, db_session):
        # Same cart total, but session budget consumed elsewhere first.
        from backend.models.order import Order
        from backend.models.cart import Cart
        from backend.services.state_machine import state_machine, SessionState

        p1 = seed_data["p1"]
        cart = client.post("/api/cart", json={"session_id": "stale-sess-4", "merchant_id": 1}).json()
        client.post(f"/api/cart/{cart['id']}/items", json={"product_id": p1.id, "quantity": 1})
        state_machine.set_state("stale-sess-4", SessionState.DISCOVERING)
        state_machine.set_state("stale-sess-4", SessionState.CART_BUILDING)
        state_machine.set_state("stale-sess-4", SessionState.POLICY_CHECK)
        appr = client.post(
            "/api/checkout/request-approval",
            json={"cart_id": cart["id"], "session_id": "stale-sess-4"}
        ).json()
        client.post(f"/api/checkout/approve/{appr['id']}", json={
            "session_id": "stale-sess-4", "approval_token": appr["approval_token"]})

        # Another order pays out most of the session budget first.
        db_cart = db_session.query(Cart).filter(Cart.id == cart["id"]).one()
        db_session.add(Order(
            order_number="DRIFT-1", merchant_id=db_cart.merchant_id,
            customer_id=db_cart.customer_id, session_id="stale-sess-4",
            cart_id=db_cart.id, subtotal_paise=900000, total_paise=900000,
            status="paid", is_ai_assisted=False, upsell_revenue_paise=0
        ))
        db_session.commit()

        resp = client.post(
            f"/api/payment/create-order/{appr['id']}", json={"session_id": "stale-sess-4"}
        )
        assert resp.status_code == 409
        assert "Policy no longer allows" in resp.json()["detail"]
