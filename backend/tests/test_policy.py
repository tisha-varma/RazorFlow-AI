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

    def test_upsell_limit_blocks(self, db_session, seed_data):
        from backend.models.policy import CommercePolicy
        policy = seed_data["policy"]
        policy.max_transaction_amount_paise = 10000000
        policy.max_quantity_per_item = 100
        db_session.commit()

        merchant = seed_data["merchant"]
        p3 = seed_data["p3"]

        cart = Cart(session_id="test-sess", merchant_id=merchant.id, status="active")
        db_session.add(cart)
        db_session.flush()

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
