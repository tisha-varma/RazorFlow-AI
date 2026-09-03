"""Seed deterministic historical demo orders (HIST-*) for the merchant dashboard.

Why this exists (review DESIGN-1): a revenue story needs aggregate volume,
and 1-2 live test orders read as empty. These rows are REAL database rows
(paid orders with items, approvals, payments, sessions) - not mock numbers
in the UI - and are trivially identifiable by their HIST- order numbers and
hist-* sessions. Rerunning wipes and recreates them (idempotent).

Usage: backend\\venv\\Scripts\\python.exe backend/seed_demo_history.py [--count 24]
"""
import sys
from datetime import datetime, timedelta

sys.path.insert(0, "C:/projects/RazorFLow AI/backend")
sys.path.insert(0, "C:/projects/RazorFLow AI")

COUNT = 24
if "--count" in sys.argv:
    COUNT = int(sys.argv[sys.argv.index("--count") + 1])

from backend.database import SessionLocal
from backend.models.cart import Cart, CartItem
from backend.models.order import Order, OrderItem
from backend.models.payment import RazorpayPayment
from backend.models.approval import Approval
from backend.models.ai_interaction import AIInteraction
from backend.models.product import Product

db = SessionLocal()
try:
    # Idempotent: clear prior HIST- demo history first.
    hist_orders = db.query(Order).filter(Order.order_number.like("HIST-%")).all()
    hist_ids = [o.id for o in hist_orders]
    if hist_ids:
        db.query(OrderItem).filter(OrderItem.order_id.in_(hist_ids)).delete(
            synchronize_session=False)
        db.query(RazorpayPayment).filter(
            RazorpayPayment.order_id.in_(hist_ids)).delete(synchronize_session=False)
        for o in hist_orders:
            db.delete(o)
    db.query(Approval).filter(Approval.session_id.like("hist-%")).delete(
        synchronize_session=False)
    db.query(AIInteraction).filter(AIInteraction.session_id.like("hist-%")).delete(
        synchronize_session=False)
    db.query(Cart).filter(Cart.session_id.like("hist-%")).delete(
        synchronize_session=False)
    db.commit()

    shoes = db.query(Product).filter(
        Product.category.in_(["Running Shoes", "Trail Shoes", "Racing Shoes"]),
        Product.is_active == True
    ).order_by(Product.id).all()
    socks = db.query(Product).filter(Product.name.ilike("%sock%")).first()
    merchant_id = shoes[0].merchant_id
    now = datetime.now()

    for i in range(COUNT):
        sess = f"hist-d{i // 4}-{i}"
        day_offset = (i * 5) % 7  # spread across the last 7 days, deterministic
        # Day-0 orders pin to right now so "today" is never empty at any hour.
        hours = 0 if day_offset == 0 else (i % 12) + 1
        created = now - timedelta(days=day_offset, hours=hours)
        main = shoes[i % len(shoes)]
        with_upsell = (i % 3 == 0) and socks is not None and socks.id != main.id

        cart = Cart(session_id=sess, merchant_id=merchant_id, status="checked_out")
        db.add(cart)
        db.flush()
        db.add(CartItem(cart_id=cart.id, product_id=main.id, variant_id=None,
                        quantity=1, unit_price_paise=main.base_price_paise,
                        is_upsell=False))
        if with_upsell:
            db.add(CartItem(cart_id=cart.id, product_id=socks.id, variant_id=None,
                            quantity=1, unit_price_paise=socks.base_price_paise,
                            is_upsell=True))
        db.flush()

        total = main.base_price_paise + (socks.base_price_paise if with_upsell else 0)
        order = Order(
            order_number=f"HIST-{i + 1:03d}", merchant_id=merchant_id,
            customer_id="demo_customer", session_id=sess, cart_id=cart.id,
            subtotal_paise=total, total_paise=total, status="paid",
            is_ai_assisted=True,
            upsell_revenue_paise=socks.base_price_paise if with_upsell else 0,
            razorpay_order_id=f"order_hist{i + 1:03d}", created_at=created
        )
        db.add(order)
        db.flush()
        db.add(OrderItem(order_id=order.id, product_id=main.id, variant_id=None,
                         product_name=main.name, quantity=1,
                         unit_price_paise=main.base_price_paise,
                         total_paise=main.base_price_paise, is_upsell=False))
        if with_upsell:
            db.add(OrderItem(order_id=order.id, product_id=socks.id, variant_id=None,
                             product_name=socks.name, quantity=1,
                             unit_price_paise=socks.base_price_paise,
                             total_paise=socks.base_price_paise, is_upsell=True))
        db.add(Approval(session_id=sess, cart_id=cart.id, order_id=order.id,
                        requested_amount_paise=total, status="approved",
                        summary_json={}, approved_at=created, created_at=created))
        db.add(RazorpayPayment(
            order_id=order.id, razorpay_order_id=f"order_hist{i + 1:03d}",
            razorpay_payment_id=f"pay_hist{i + 1:03d}", amount_paise=total,
            currency="INR", status="captured", verified=True))
        db.add(AIInteraction(session_id=sess, merchant_id=merchant_id,
                             interaction_type="search", user_message="demo history",
                             ai_response="demo history", tool_calls=[]))
    db.commit()
    print(f"seeded {COUNT} HIST- orders (cart+items, approval, payment, session each)")
finally:
    db.close()
