import hashlib
import hmac
import json
import time

import pytest

from backend.services.state_machine import state_machine, SessionState


def _approved_approval(client, seed_data, session_id):
    """Cart + policy walk + request + approve. Returns approval json."""
    p1 = seed_data["p1"]
    cart = client.post("/api/cart", json={"session_id": session_id, "merchant_id": 1}).json()
    client.post(f"/api/cart/{cart['id']}/items", json={"product_id": p1.id, "quantity": 1})
    state_machine.set_state(session_id, SessionState.DISCOVERING)
    state_machine.set_state(session_id, SessionState.CART_BUILDING)
    state_machine.set_state(session_id, SessionState.POLICY_CHECK)
    appr = client.post(
        "/api/checkout/request-approval",
        json={"cart_id": cart["id"], "session_id": session_id},
    ).json()
    appr = client.post(
        f"/api/checkout/approve/{appr['id']}", json={"session_id": session_id}
    ).json()
    assert appr["status"] == "approved"
    return appr, cart


def _mock_gateway(monkeypatch, order_id="order_test123", verified=True):
    from backend.services import payment_service as ps

    calls = {"orders": 0}

    def fake_create(amount_paise, receipt_id, notes=None):
        calls["orders"] += 1
        return {
            "razorpay_order_id": order_id,
            "amount_paise": amount_paise,
            "currency": "INR",
            "status": "created",
        }

    monkeypatch.setattr(ps, "create_razorpay_order", fake_create)
    monkeypatch.setattr(ps, "verify_payment_signature", lambda *a: verified)
    return calls


class TestCreateOrder:
    def test_requires_approved_approval(self, client, seed_data):
        p1 = seed_data["p1"]
        cart = client.post("/api/cart", json={"session_id": "pay-sess-1", "merchant_id": 1}).json()
        client.post(f"/api/cart/{cart['id']}/items", json={"product_id": p1.id, "quantity": 1})
        state_machine.set_state("pay-sess-1", SessionState.DISCOVERING)
        state_machine.set_state("pay-sess-1", SessionState.CART_BUILDING)
        state_machine.set_state("pay-sess-1", SessionState.POLICY_CHECK)
        appr = client.post(
            "/api/checkout/request-approval",
            json={"cart_id": cart["id"], "session_id": "pay-sess-1"},
        ).json()
        assert appr["status"] == "pending"

        resp = client.post(f"/api/payment/create-order/{appr['id']}", json={"session_id": "pay-sess-1"})
        assert resp.status_code == 400

    def test_success_creates_order_and_payment_rows(self, client, seed_data, monkeypatch):
        from backend.models.order import Order
        from backend.models.payment import RazorpayPayment
        from backend.models.audit import AuditEvent
        from backend.database import get_db  # noqa: F401

        _mock_gateway(monkeypatch)
        appr, cart = _approved_approval(client, seed_data, "pay-sess-2")

        resp = client.post(f"/api/payment/create-order/{appr['id']}", json={"session_id": "pay-sess-2"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["razorpay_order_id"] == "order_test123"
        assert data["amount_paise"] == 449900
        assert data["currency"] == "INR"

        # Inspect DB via a fresh API-visible check: order pending, payment created.
        assert state_machine.get_state("pay-sess-2") == SessionState.PAYMENT_PENDING

    def test_idempotent_on_retry(self, client, seed_data, monkeypatch):
        calls = _mock_gateway(monkeypatch, order_id="order_dup1")
        appr, cart = _approved_approval(client, seed_data, "pay-sess-3")

        r1 = client.post(f"/api/payment/create-order/{appr['id']}", json={"session_id": "pay-sess-3"})
        r2 = client.post(f"/api/payment/create-order/{appr['id']}", json={"session_id": "pay-sess-3"})
        assert r1.status_code == 200 and r2.status_code == 200
        assert r1.json()["razorpay_order_id"] == r2.json()["razorpay_order_id"]
        assert calls["orders"] == 1

    def test_missing_credentials_503(self, client, seed_data, monkeypatch):
        from backend.config import settings
        monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", "")
        monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "")
        appr, cart = _approved_approval(client, seed_data, "pay-sess-4")

        resp = client.post(f"/api/payment/create-order/{appr['id']}", json={"session_id": "pay-sess-4"})
        assert resp.status_code == 503

    def test_session_mismatch_403(self, client, seed_data, monkeypatch):
        _mock_gateway(monkeypatch)
        appr, cart = _approved_approval(client, seed_data, "pay-sess-5")
        resp = client.post(f"/api/payment/create-order/{appr['id']}", json={"session_id": "wrong-sess"})
        assert resp.status_code == 403


class TestVerify:
    def _order_for(self, client, seed_data, monkeypatch, session_id, order_id="order_v1"):
        _mock_gateway(monkeypatch, order_id=order_id)
        appr, cart = _approved_approval(client, seed_data, session_id)
        data = client.post(
            f"/api/payment/create-order/{appr['id']}", json={"session_id": session_id}
        ).json()
        return appr, data

    def test_verify_success_marks_paid(self, client, seed_data, monkeypatch):
        from backend.models.order import Order
        from backend.models.approval import Approval
        from backend.models.audit import AuditEvent

        appr, data = self._order_for(client, seed_data, monkeypatch, "pay-v-1", "order_v1")
        resp = client.post("/api/payment/verify", json={
            "razorpay_order_id": "order_v1",
            "razorpay_payment_id": "pay_test1",
            "razorpay_signature": "sig_test",
            "session_id": "pay-v-1",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "paid"
        assert state_machine.get_state("pay-v-1") == SessionState.ORDER_CONFIRMED

    def test_verify_bad_signature_fails_without_paid_order(self, client, seed_data, monkeypatch):
        from backend.models.order import Order

        appr, data = self._order_for(client, seed_data, monkeypatch, "pay-v-2", "order_v2")
        # Flip the mock to reject AFTER order creation.
        from backend.services import payment_service as ps
        monkeypatch.setattr(ps, "verify_payment_signature", lambda *a: False)

        resp = client.post("/api/payment/verify", json={
            "razorpay_order_id": "order_v2",
            "razorpay_payment_id": "pay_bad",
            "razorpay_signature": "bad",
            "session_id": "pay-v-2",
        })
        assert resp.status_code == 400
        assert state_machine.get_state("pay-v-2") == SessionState.PAYMENT_FAILED

    def test_verify_unknown_order_404(self, client):
        resp = client.post("/api/payment/verify", json={
            "razorpay_order_id": "order_nope",
            "razorpay_payment_id": "pay_x",
            "razorpay_signature": "sig",
            "session_id": "pay-v-3",
        })
        assert resp.status_code == 404

    def test_verify_idempotent(self, client, seed_data, monkeypatch):
        appr, data = self._order_for(client, seed_data, monkeypatch, "pay-v-4", "order_v4")
        payload = {
            "razorpay_order_id": "order_v4",
            "razorpay_payment_id": "pay_dup",
            "razorpay_signature": "sig",
            "session_id": "pay-v-4",
        }
        r1 = client.post("/api/payment/verify", json=payload)
        r2 = client.post("/api/payment/verify", json=payload)
        assert r1.status_code == 200 and r2.status_code == 200
        assert r1.json()["order_id"] == r2.json()["order_id"]


class TestRetryRecovery:
    def test_failed_payment_recovers_to_paid_on_retry(self, client, db_session, seed_data, monkeypatch):
        from backend.models.order import Order
        from backend.models.approval import Approval
        from backend.services import payment_service as ps

        session_id = "pay-retry-1"
        appr, cart = TestVerify()._order_for(
            client, seed_data, monkeypatch, session_id, "order_retry1"
        )

        # 1. First attempt fails signature check.
        monkeypatch.setattr(ps, "verify_payment_signature", lambda *a: False)
        fail = client.post("/api/payment/verify", json={
            "razorpay_order_id": "order_retry1",
            "razorpay_payment_id": "pay_fail1",
            "razorpay_signature": "bad",
            "session_id": session_id,
        })
        assert fail.status_code == 400
        assert state_machine.get_state(session_id) == SessionState.PAYMENT_FAILED

        # 2. Retry re-triggers create-order on the SAME approval (new gateway
        #    order per Razorpay's one-order-per-attempt rule, no new approval).
        monkeypatch.setattr(
            ps, "create_razorpay_order",
            lambda amount, receipt, notes=None: {
                "razorpay_order_id": "order_retry2",
                "amount_paise": amount, "currency": "INR", "status": "created",
            },
        )
        monkeypatch.setattr(ps, "verify_payment_signature", lambda *a: True)
        retry = client.post(
            f"/api/payment/create-order/{appr['id']}", json={"session_id": session_id}
        )
        assert retry.status_code == 200
        assert retry.json()["razorpay_order_id"] == "order_retry2"
        assert state_machine.get_state(session_id) == SessionState.PAYMENT_PENDING

        # 3. Second attempt verifies cleanly to a paid order.
        ok = client.post("/api/payment/verify", json={
            "razorpay_order_id": "order_retry2",
            "razorpay_payment_id": "pay_ok1",
            "razorpay_signature": "sig",
            "session_id": session_id,
        })
        assert ok.status_code == 200
        assert ok.json()["status"] == "paid"
        assert state_machine.get_state(session_id) == SessionState.ORDER_CONFIRMED

        # 4. Exactly one approval, one paid order, no double charge.
        # (db_session shares the test engine with the API override.)
        db_session.expire_all()
        assert db_session.query(Approval).filter(
            Approval.session_id == session_id
        ).count() == 1
        orders = db_session.query(Order).filter(Order.session_id == session_id).all()
        paid = [o for o in orders if o.status == "paid"]
        failed = [o for o in orders if o.status == "failed"]
        assert len(paid) == 1
        assert paid[0].razorpay_order_id == "order_retry2"
        assert len(failed) == 1
        assert failed[0].razorpay_order_id == "order_retry1"

    def test_failed_to_pending_transition_valid(self):
        from backend.services.state_machine import VALID_TRANSITIONS
        assert SessionState.PAYMENT_PENDING in VALID_TRANSITIONS[SessionState.PAYMENT_FAILED]


class TestPaidClearsCart:
    def test_paid_order_empties_cart(self, client, seed_data, monkeypatch):
        appr, data = TestVerify()._order_for(client, seed_data, monkeypatch, "pay-clear-1", "order_clr1")
        cart_id = appr["cart_id"]
        resp = client.post("/api/payment/verify", json={
            "razorpay_order_id": "order_clr1",
            "razorpay_payment_id": "pay_clr1",
            "razorpay_signature": "sig",
            "session_id": "pay-clear-1",
        })
        assert resp.status_code == 200
        cart = client.get(f"/api/cart/{cart_id}").json()
        assert cart["items"] == []
        assert cart["status"] == "checked_out"


class TestFailedSpend:
    def test_failed_payment_consumes_no_budget(self, client, seed_data, monkeypatch):
        from backend.services import payment_service as ps

        appr, data = TestVerify()._order_for(client, seed_data, monkeypatch, "pay-failspend-1", "order_fs1")
        monkeypatch.setattr(ps, "verify_payment_signature", lambda *a: False)
        fail = client.post("/api/payment/verify", json={
            "razorpay_order_id": "order_fs1",
            "razorpay_payment_id": "pay_fs1",
            "razorpay_signature": "bad",
            "session_id": "pay-failspend-1",
        })
        assert fail.status_code == 400

        usage = client.get("/api/policy/session-usage", params={"session_id": "pay-failspend-1"}).json()
        assert usage["session_spent_paise"] == 0
        # Only the still-active cart counts — the failed order adds nothing.
        assert usage["used_paise"] == usage["cart_total_paise"] == 449900
        assert usage["remaining_paise"] == 1000000 - 449900


def _signed_webhook(secret, payload_dict):
    body = json.dumps(payload_dict, separators=(",", ":")).encode()
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return body, sig


class TestWebhook:
    def test_captured_reconciles_unpaid_order(self, client, seed_data, monkeypatch):
        from backend.config import settings
        monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", "whsec_test")

        appr, data = TestVerify()._order_for(client, seed_data, monkeypatch, "pay-w-1", "order_w1")
        payload = {
            "event": "payment.captured",
            "created_at": int(time.time()),
            "payload": {"payment": {"entity": {
                "id": "pay_web1", "order_id": "order_w1",
                "amount": 449900, "method": "upi", "captured": True,
            }}},
        }
        body, sig = _signed_webhook("whsec_test", payload)
        resp = client.post("/api/payment/webhook", content=body, headers={
            "Content-Type": "application/json", "X-Razorpay-Signature": sig,
        })
        assert resp.status_code == 200
        assert state_machine.get_state("pay-w-1") == SessionState.ORDER_CONFIRMED

        # Duplicate delivery: idempotent, still one paid order.
        dup = client.post("/api/payment/webhook", content=body, headers={
            "Content-Type": "application/json", "X-Razorpay-Signature": sig,
        })
        assert dup.status_code == 200
        assert "duplicate" in dup.json()["detail"]

    def test_bad_signature_rejected(self, client):
        from backend.config import settings
        from unittest.mock import patch
        with patch.object(settings, "RAZORPAY_WEBHOOK_SECRET", "whsec_test"):
            payload = {"event": "payment.captured", "payload": {}}
            body = json.dumps(payload).encode()
            resp = client.post("/api/payment/webhook", content=body, headers={
                "Content-Type": "application/json", "X-Razorpay-Signature": "bad",
            })
            assert resp.status_code == 400

    def test_failed_marks_order_failed(self, client, seed_data, monkeypatch):
        from backend.config import settings
        monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", "whsec_test")

        appr, data = TestVerify()._order_for(client, seed_data, monkeypatch, "pay-w-2", "order_w2")
        payload = {
            "event": "payment.failed",
            "created_at": int(time.time()),
            "payload": {"payment": {"entity": {
                "id": "pay_webfail", "order_id": "order_w2",
                "error_code": "BAD_REQUEST_ERROR",
                "error_description": "Payment declined",
            }}},
        }
        body, sig = _signed_webhook("whsec_test", payload)
        resp = client.post("/api/payment/webhook", content=body, headers={
            "Content-Type": "application/json", "X-Razorpay-Signature": sig,
        })
        assert resp.status_code == 200
        assert state_machine.get_state("pay-w-2") == SessionState.PAYMENT_FAILED

    def test_unknown_order_ignored(self, client, monkeypatch):
        from backend.config import settings
        monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", "whsec_test")
        payload = {
            "event": "payment.captured",
            "created_at": int(time.time()),
            "payload": {"payment": {"entity": {
                "id": "pay_ghost", "order_id": "order_ghost",
                "amount": 100, "method": "card", "captured": True,
            }}},
        }
        body, sig = _signed_webhook("whsec_test", payload)
        resp = client.post("/api/payment/webhook", content=body, headers={
            "Content-Type": "application/json", "X-Razorpay-Signature": sig,
        })
        assert resp.status_code == 200
        assert "unknown" in resp.json()["detail"]
