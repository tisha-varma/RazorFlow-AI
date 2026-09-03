import pytest
from backend.services.policy_engine import PolicyEngine
from backend.models.cart import Cart, CartItem


class TestPolicyEngine:
    def test_under_limit_passes(self, db_session, seed_data):
        policy = seed_data["policy"]
        merchant = seed_data["merchant"]
        p1 = seed_data["p1"]

        cart = Cart(session_id="test-sess", merchant_id=merchant.id, status="active")
        db_session.add(cart)
        db_session.flush()

        item = CartItem(
            cart_id=cart.id,
            product_id=p1.id,
            quantity=1,
            unit_price_paise=449900,
            is_upsell=False
        )
        db_session.add(item)
        db_session.commit()

        result = PolicyEngine.check_purchase_policy(db_session, cart.id, "test-sess", policy)
        assert result.allowed is True
        assert result.reason is None

    def test_at_limit_passes(self, db_session, seed_data):
        policy = seed_data["policy"]
        merchant = seed_data["merchant"]
        p1 = seed_data["p1"]

        cart = Cart(session_id="test-sess", merchant_id=merchant.id, status="active")
        db_session.add(cart)
        db_session.flush()

        item = CartItem(
            cart_id=cart.id,
            product_id=p1.id,
            quantity=1,
            unit_price_paise=500000,
            is_upsell=False
        )
        db_session.add(item)
        db_session.commit()

        result = PolicyEngine.check_purchase_policy(db_session, cart.id, "test-sess", policy)
        assert result.allowed is True

    def test_over_limit_blocks(self, db_session, seed_data):
        policy = seed_data["policy"]
        merchant = seed_data["merchant"]
        p1 = seed_data["p1"]

        cart = Cart(session_id="test-sess", merchant_id=merchant.id, status="active")
        db_session.add(cart)
        db_session.flush()

        item = CartItem(
            cart_id=cart.id,
            product_id=p1.id,
            quantity=2,
            unit_price_paise=449900,
            is_upsell=False
        )
        db_session.add(item)
        db_session.commit()

        result = PolicyEngine.check_purchase_policy(db_session, cart.id, "test-sess", policy)
        assert result.allowed is False
        assert "exceeds" in result.reason.lower()

    def test_empty_cart_blocks(self, db_session, seed_data):
        policy = seed_data["policy"]
        merchant = seed_data["merchant"]

        cart = Cart(session_id="test-sess", merchant_id=merchant.id, status="active")
        db_session.add(cart)
        db_session.commit()

        result = PolicyEngine.check_purchase_policy(db_session, cart.id, "test-sess", policy)
        assert result.allowed is False
        assert "empty" in result.reason.lower()

    def test_quantity_limit_blocks(self, db_session, seed_data):
        from backend.models.policy import CommercePolicy
        policy = seed_data["policy"]
        policy.max_transaction_amount_paise = 10000000
        db_session.commit()

        merchant = seed_data["merchant"]
        p1 = seed_data["p1"]

        cart = Cart(session_id="test-sess", merchant_id=merchant.id, status="active")
        db_session.add(cart)
        db_session.flush()

        item = CartItem(
            cart_id=cart.id,
            product_id=p1.id,
            quantity=10,
            unit_price_paise=449900,
            is_upsell=False
        )
        db_session.add(item)
        db_session.commit()

        db_session.refresh(policy)
        result = PolicyEngine.check_purchase_policy(db_session, cart.id, "test-sess", policy)
        assert result.allowed is False
        assert "quantity" in result.reason.lower()

    def test_session_usage_reports_limit_and_remaining(self, client, seed_data):
        p1 = seed_data["p1"]
        cart = client.post("/api/cart", json={"session_id": "usage-sess", "merchant_id": 1}).json()
        client.post(f"/api/cart/{cart['id']}/items", json={"product_id": p1.id, "quantity": 1})
        resp = client.get("/api/policy/session-usage", params={"session_id": "usage-sess"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["spending_limit_paise"] == 1000000
        assert data["cart_total_paise"] == 449900
        assert data["session_spent_paise"] == 0
        assert data["used_paise"] == 449900
        assert data["remaining_paise"] == 550100

    def test_session_usage_empty_cart(self, client, seed_data):
        resp = client.get("/api/policy/session-usage", params={"session_id": "usage-empty"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["used_paise"] == 0
        assert data["remaining_paise"] == data["spending_limit_paise"]

    def test_upsell_limit_blocks(self, db_session, seed_data):
        from backend.models.policy import CommercePolicy
        policy = seed_data["policy"]
        policy.max_transaction_amount_paise = 10000000
        policy.max_quantity_per_item = 100
        db_session.commit()

        merchant = seed_data["merchant"]
        p1 = seed_data["p1"]
        p3 = seed_data["p3"]

        cart = Cart(session_id="test-sess", merchant_id=merchant.id, status="active")
        db_session.add(cart)
        db_session.flush()

        # A real base item so this tests the upsell CAP, not the
        # non-upsell-presence rule below.
        db_session.add(CartItem(
            cart_id=cart.id,
            product_id=p1.id,
            quantity=1,
            unit_price_paise=449900,
            is_upsell=False
        ))
        item = CartItem(
            cart_id=cart.id,
            product_id=p3.id,
            quantity=1,
            unit_price_paise=49900,
            is_upsell=True
        )
        db_session.add(item)
        db_session.flush()

        override = CartItem(
            cart_id=cart.id,
            product_id=p3.id,
            quantity=10,
            unit_price_paise=49900,
            is_upsell=True
        )
        db_session.add(override)
        db_session.commit()

        db_session.refresh(policy)
        result = PolicyEngine.check_purchase_policy(db_session, cart.id, "test-sess", policy)
        assert result.allowed is False
        assert "upsell" in result.reason.lower()

    def test_all_upsell_cart_blocked(self, db_session, seed_data):
        policy = seed_data["policy"]
        merchant = seed_data["merchant"]
        p3 = seed_data["p3"]

        cart = Cart(session_id="upsell-only", merchant_id=merchant.id, status="active")
        db_session.add(cart)
        db_session.flush()
        db_session.add(CartItem(
            cart_id=cart.id, product_id=p3.id, quantity=1,
            unit_price_paise=49900, is_upsell=True
        ))
        db_session.commit()

        result = PolicyEngine.check_purchase_policy(db_session, cart.id, "upsell-only", policy)
        assert result.allowed is False
        assert "non-upsell" in result.reason.lower()

    def test_minimum_floor_blocks_and_defaults_open(self, db_session, seed_data):
        policy = seed_data["policy"]
        merchant = seed_data["merchant"]
        p3 = seed_data["p3"]

        def cart_with(price, sess):
            cart = Cart(session_id=sess, merchant_id=merchant.id, status="active")
            db_session.add(cart)
            db_session.flush()
            db_session.add(CartItem(
                cart_id=cart.id, product_id=p3.id, quantity=1,
                unit_price_paise=price, is_upsell=False
            ))
            db_session.commit()
            return cart

        # Default 0 disables the floor.
        assert policy.min_transaction_amount_paise == 0
        c1 = cart_with(100, "min-sess-1")
        assert PolicyEngine.check_purchase_policy(
            db_session, c1.id, "min-sess-1", policy).allowed is True

        # A set floor blocks trivially small carts.
        policy.min_transaction_amount_paise = 10000
        db_session.commit()
        db_session.refresh(policy)
        c2 = cart_with(100, "min-sess-2")
        blocked = PolicyEngine.check_purchase_policy(db_session, c2.id, "min-sess-2", policy)
        assert blocked.allowed is False
        assert "minimum" in blocked.reason.lower()
