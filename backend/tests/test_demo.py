import pytest


def _mock_rzp_order(monkeypatch, order_id="order_demo_test"):
    from backend.services import payment_service as ps
    monkeypatch.setattr(
        ps, "create_razorpay_order",
        lambda amount, receipt, notes=None: {
            "razorpay_order_id": order_id, "amount_paise": amount,
            "currency": "INR", "status": "created"
        }
    )


class TestDemoReset:
    def test_reset_clears_and_restores_defaults(self, client, db_session, seed_data):
        from backend.models.cart import Cart
        from backend.models.policy import CommercePolicy
        from backend.services.state_machine import state_machine, SessionState

        p1 = seed_data["p1"]
        cart = client.post("/api/cart", json={"session_id": "demo-rs", "merchant_id": 1}).json()
        client.post(f"/api/cart/{cart['id']}/items", json={"product_id": p1.id, "quantity": 1})
        state_machine.set_state("demo-rs", SessionState.DISCOVERING)

        # Break the policy first to prove reset restores it.
        policy = db_session.query(CommercePolicy).first()
        policy.max_quantity_per_item = 99
        db_session.commit()

        resp = client.post("/api/demo/reset", params={"session_id": "demo-rs"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["cleared_states"] == 1
        assert body["cleared_rows"]["carts"] >= 1

        db_session.expire_all()
        assert db_session.query(Cart).filter(Cart.session_id == "demo-rs").count() == 0
        assert state_machine.get_state("demo-rs") == SessionState.IDLE
        policy = db_session.query(CommercePolicy).first()
        assert policy.max_quantity_per_item == 5
        assert policy.spending_limit_paise == 1000000
        assert policy.require_approval is True


class TestDemoTriggers:
    def test_successful_purchase_paid(self, client, db_session, seed_data, monkeypatch):
        from backend.models.order import Order
        from backend.models.audit import AuditEvent

        _mock_rzp_order(monkeypatch, "order_demo_ok")
        resp = client.post("/api/demo/run-successful-purchase", params={"session_id": "demo-ok"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "paid"
        assert body["razorpay_order_id"] == "order_demo_ok"
        assert body["simulated_capture"] is True
        assert any("upsell" in s for s in body["steps"])

        db_session.expire_all()
        order = db_session.query(Order).filter(Order.session_id == "demo-ok").one()
        assert order.status == "paid"
        assert order.is_ai_assisted is False
        success = db_session.query(AuditEvent).filter(
            AuditEvent.event_type == "PAYMENT_SUCCESS",
            AuditEvent.related_entity_id == order.id
        ).all()
        assert len(success) == 1  # no duplicate success events
        # Honesty lives in its own append-only event now: the SUCCESS row
        # must stay pristine so its chain hash verifies.
        assert "simulated" not in success[0].event_data
        sim = db_session.query(AuditEvent).filter(
            AuditEvent.event_type == "DEMO_SIMULATED_CAPTURE",
            AuditEvent.related_entity_id == order.id
        ).all()
        assert len(sim) == 1
        assert sim[0].event_data["simulated"] is True
        assert sim[0].event_data["source"] == "demo-trigger"

    def test_payment_failure_marks_failed(self, client, db_session, seed_data, monkeypatch):
        from backend.models.order import Order

        _mock_rzp_order(monkeypatch, "order_demo_fail")
        resp = client.post("/api/demo/run-payment-failure", params={"session_id": "demo-fail"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "failed"

        db_session.expire_all()
        order = db_session.query(Order).filter(Order.session_id == "demo-fail").one()
        assert order.status == "failed"

    def test_upsell_scenario_returns_candidates(self, client, seed_data):
        resp = client.post("/api/demo/run-upsell-scenario", params={"session_id": "demo-up"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["added"] == "RunPro Sprint"
        assert len(body["upsell"]) >= 1
        assert "Running Socks" in body["upsell"][0]["name"]


class TestDemoGate:
    def test_status_reflects_flag(self, client, monkeypatch):
        from backend.config import settings
        assert client.get("/api/demo/status").json() == {"demo_mode": True}
        monkeypatch.setattr(settings, "DEMO_MODE", False)
        assert client.get("/api/demo/status").json() == {"demo_mode": False}
        assert client.post("/api/demo/reset").status_code == 403
        assert client.post("/api/demo/run-successful-purchase").status_code == 403


class TestPolicyBlockDemo:
    def test_over_limit_cart_blocked_without_approval(self, client, seed_data):
        from backend.models.approval import Approval
        from backend.database import get_db

        resp = client.post("/api/demo/run-policy-block", params={"session_id": "demo-pol"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "blocked"
        assert body["allowed"] is False
        assert body["cart_total_paise"] == 2 * 449900
        assert len(body["steps"]) >= 3

        # The gate refuses before any artifact: no approval was minted.
        db = next(get_db())
        try:
            assert db.query(Approval).filter(
                Approval.session_id == "demo-pol").count() == 0
        finally:
            db.close()

    def test_policy_block_gated(self, client, monkeypatch):
        from backend.config import settings
        monkeypatch.setattr(settings, "DEMO_MODE", False)
        assert client.post("/api/demo/run-policy-block").status_code == 403


class TestSeedHistory:
    def test_seed_history_idempotent(self, client):
        from backend.models.order import Order
        from backend.database import get_db

        r1 = client.post("/api/demo/seed-history", params={"count": 6})
        assert r1.status_code == 200
        assert r1.json()["seeded"] == 6

        db = next(get_db())
        try:
            first = sorted(o.order_number for o in db.query(Order).filter(
                Order.order_number.like("HIST-%")).all())
            assert first == [f"HIST-{i + 1:03d}" for i in range(6)]
        finally:
            db.close()

        # Reseed replaces, never duplicates.
        r2 = client.post("/api/demo/seed-history", params={"count": 6})
        assert r2.json()["seeded"] == 6
        db = next(get_db())
        try:
            assert db.query(Order).filter(
                Order.order_number.like("HIST-%")).count() == 6
        finally:
            db.close()

    def test_seed_history_gated(self, client, monkeypatch):
        from backend.config import settings
        monkeypatch.setattr(settings, "DEMO_MODE", False)
        assert client.post("/api/demo/seed-history").status_code == 403
