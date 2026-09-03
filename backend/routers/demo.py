"""Demo controls: reset + scripted, LLM-free scenario triggers.

Dev/demo only - every route here is gated on settings.DEMO_MODE so the
panel disappears from anything resembling a production view.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.config import settings
from backend.models.approval import Approval
from backend.models.audit import AuditEvent
from backend.models.ai_interaction import AIInteraction
from backend.models.cart import Cart, CartItem
from backend.models.merchant import Merchant
from backend.models.order import Order, OrderItem
from backend.models.payment import RazorpayPayment
from backend.models.policy import CommercePolicy
from backend.models.session_state import SessionStateEvent

router = APIRouter(prefix="/demo", tags=["Demo"])

# Single source for demo policy defaults (not scattered as constants).
DEMO_POLICY_DEFAULTS = {
    "max_transaction_amount_paise": 500000,   # Rs 5,000
    "min_transaction_amount_paise": 0,        # no floor
    "require_approval": True,
    "max_quantity_per_item": 5,
    "allow_upsell": True,
    "max_upsell_amount_paise": 200000,        # Rs 2,000
    "allow_auto_retry": False,
    "spending_limit_paise": 1000000,          # Rs 10,000
    "is_active": True,
}

DEMO_PRODUCT = "RunPro Sprint"


def _require_demo():
    if not settings.DEMO_MODE:
        raise HTTPException(status_code=403, detail="Demo mode is disabled")


@router.get("/status")
def demo_status():
    return {"demo_mode": bool(settings.DEMO_MODE)}


@router.post("/reset")
def reset_demo(session_id: str | None = None, db: Session = Depends(get_db)):
    """Clear demo data and restore defaults. Scoped to a session when given,
    otherwise merchant-wide (merchant 1)."""
    _require_demo()

    merchant = db.query(Merchant).first()
    merchant_id = merchant.id if merchant else 1

    # Resolve the in-scope parents FIRST, then delete strictly by those ids.
    # (A blanket model-wide delete here once wiped every order item and
    # payment in the database - never again.)
    if session_id:
        cart_ids = [c.id for c in db.query(Cart.id).filter(
            Cart.session_id == session_id).all()]
        order_ids = [o.id for o in db.query(Order.id).filter(
            Order.session_id == session_id).all()]
    else:
        cart_ids = [c.id for c in db.query(Cart.id).filter(
            Cart.merchant_id == merchant_id).all()]
        order_ids = [o.id for o in db.query(Order.id).filter(
            Order.merchant_id == merchant_id).all()]

    counts = {}
    counts["cart_items"] = db.query(CartItem).filter(
        CartItem.cart_id.in_(cart_ids)).delete(synchronize_session=False) if cart_ids else 0
    counts["order_items"] = db.query(OrderItem).filter(
        OrderItem.order_id.in_(order_ids)).delete(synchronize_session=False) if order_ids else 0
    counts["razorpay_payments"] = db.query(RazorpayPayment).filter(
        RazorpayPayment.order_id.in_(order_ids)).delete(synchronize_session=False) if order_ids else 0

    def _scope_event(query, model):
        if session_id:
            return query.filter(model.session_id == session_id)
        if hasattr(model, "merchant_id"):
            return query.filter(
                (model.merchant_id == merchant_id) | (model.merchant_id.is_(None))
            )
        return query

    approval_q = db.query(Approval)
    if session_id:
        approval_q = approval_q.filter(Approval.session_id == session_id)
    elif cart_ids:
        approval_q = approval_q.filter(Approval.cart_id.in_(cart_ids))
    else:
        approval_q = approval_q.filter(False)
    counts["approvals"] = approval_q.delete(synchronize_session=False)

    counts["carts"] = db.query(Cart).filter(
        Cart.id.in_(cart_ids)).delete(synchronize_session=False) if cart_ids else 0
    counts["orders"] = db.query(Order).filter(
        Order.id.in_(order_ids)).delete(synchronize_session=False) if order_ids else 0

    counts["audit_events"] = _scope_event(db.query(AuditEvent), AuditEvent).delete(
        synchronize_session=False)
    counts["ai_interactions"] = _scope_event(db.query(AIInteraction), AIInteraction).delete(
        synchronize_session=False)
    counts["session_state_events"] = _scope_event(
        db.query(SessionStateEvent), SessionStateEvent).delete(synchronize_session=False)
    db.commit()

    # Restore the default active policy (upsert, single source of defaults).
    policy = db.query(CommercePolicy).filter(
        CommercePolicy.merchant_id == merchant_id,
        CommercePolicy.is_active == True
    ).first()
    if policy:
        for key, value in DEMO_POLICY_DEFAULTS.items():
            setattr(policy, key, value)
    else:
        policy = CommercePolicy(merchant_id=merchant_id, **DEMO_POLICY_DEFAULTS)
        db.add(policy)
    db.commit()

    # Clear in-memory session state + agent history.
    cleared_states = 0
    cleared_history = 0
    try:
        from backend.services.state_machine import state_machine
        if session_id:
            cleared_states = 1 if state_machine._sessions.pop(session_id, None) is not None else 0
        else:
            cleared_states = len(state_machine._sessions)
            state_machine._sessions.clear()
    except Exception:
        pass
    try:
        from backend.routers.agent import get_agent
        agent = get_agent()
        if session_id:
            cleared_history = 1 if agent._history.pop(session_id, None) is not None else 0
            agent._last_search.pop(session_id, None)
            agent._seen_product_ids.pop(session_id, None)
        else:
            cleared_history = len(agent._history)
            agent._history.clear()
            agent._last_search.clear()
            agent._seen_product_ids.clear()
    except Exception:
        pass

    return {
        "ok": True,
        "scope": session_id or f"merchant:{merchant_id}",
        "cleared_rows": counts,
        "cleared_states": cleared_states,
        "cleared_history": cleared_history,
        "policy": "reset to demo defaults"
    }


def _drive_flow(db: Session, session_id: str, fail_payment: bool = False) -> dict:
    """Deterministic purchase flow: search -> cart -> upsell -> policy ->
    approval -> Razorpay order -> capture/fail. No LLM involved."""
    import time
    from backend.services.catalog_service import CatalogService
    from backend.services.cart_service import CartService
    from backend.services.checkout_service import CheckoutService
    from backend.services import payment_service
    from backend.services.payment_service import PaymentConfigError
    from backend.services.state_machine import state_machine, SessionState

    started = time.time()
    log: list[str] = []

    # 1. Search a fixed known-good product.
    found, _ = CatalogService.get_products(db, query=DEMO_PRODUCT, limit=5)
    if not found:
        raise HTTPException(status_code=500, detail=f"Demo product '{DEMO_PRODUCT}' missing from catalog")
    main = next((p for p in found if p.name == DEMO_PRODUCT), found[0])
    log.append(f"search: {main.name}")

    # 2-3. Cart + main item + upsell item (first related match, flagged).
    cart = CartService.create_cart(db, session_id, 1)
    CartService.add_item(db, cart.id, main.id, quantity=1)
    related, _ = CatalogService.get_related_products_with_source(db, main.id)
    upsell = related[0] if related else None
    if upsell:
        CartService.add_item(db, cart.id, upsell.id, quantity=1, is_upsell=True)
        log.append(f"upsell: {upsell.name}")
    totals = CartService.calculate_totals(db, cart.id)

    # 4-5. Policy (automatic) + approval, approved at once.
    for target in (SessionState.DISCOVERING, SessionState.RECOMMENDING,
                   SessionState.CART_BUILDING, SessionState.POLICY_CHECK):
        state_machine.set_state(session_id, target)
    created = CheckoutService.create_approval(db, session_id, cart.id)
    if "approval" not in created:
        raise HTTPException(status_code=400, detail=created.get("policy_reason") or "Policy blocked demo cart")
    approval = created["approval"]
    approval.status = "approved"
    from datetime import datetime
    approval.approved_at = datetime.utcnow()
    db.commit()
    state_machine.set_state(session_id, SessionState.AWAITING_APPROVAL)
    state_machine.set_state(session_id, SessionState.PAYMENT_PENDING)
    log.append(f"approved: #{approval.id}")

    # 6. Real Razorpay test order when configured, simulated id otherwise.
    from backend.services.payment_service import PaymentGatewayError
    receipt = f"demo-a{approval.id}-{uuid.uuid4().hex[:8]}"
    simulated = False
    try:
        rzr = payment_service.create_razorpay_order(
            totals["total_paise"], receipt,
            notes={"approval_id": str(approval.id), "demo": "true"}
        )
        rzr_order_id = rzr["razorpay_order_id"]
    except (PaymentConfigError, PaymentGatewayError):
        rzr_order_id = f"order_demo_{uuid.uuid4().hex[:8]}"
        simulated = True
    log.append(f"razorpay order: {rzr_order_id}" + (" (simulated)" if simulated else ""))

    order = Order(
        order_number=f"DEMO-{approval.id}-{uuid.uuid4().hex[:6].upper()}",
        merchant_id=cart.merchant_id, customer_id=cart.customer_id,
        session_id=session_id, cart_id=cart.id,
        subtotal_paise=totals["subtotal_paise"], total_paise=totals["total_paise"],
        status="pending", is_ai_assisted=False,
        upsell_revenue_paise=totals.get("upsell_total_paise", 0),
        razorpay_order_id=rzr_order_id
    )
    db.add(order)
    db.flush()
    for entry in totals["items"]:
        db.add(OrderItem(
            order_id=order.id, product_id=entry["product_id"],
            variant_id=entry.get("variant_id"), product_name=entry["product_name"],
            quantity=entry["quantity"], unit_price_paise=entry["unit_price_paise"],
            total_paise=entry["total_paise"], is_upsell=entry.get("is_upsell", False)
        ))
    payment = RazorpayPayment(
        order_id=order.id, razorpay_order_id=rzr_order_id,
        amount_paise=totals["total_paise"], currency="INR",
        status="created", verified=False, idempotency_key=receipt
    )
    db.add(payment)
    db.commit()

    # 7. Capture or fail.
    from backend.routers.payment import _mark_order_paid, _mark_order_failed
    if fail_payment:
        reason = "Demo decline: card_declined (simulated gateway failure)"
        _mark_order_failed(db, order, payment, reason, actor="system")
        log.append("payment: FAILED (simulated decline)")
        return {
            "status": "failed", "session_id": session_id,
            "order_id": order.id, "order_number": order.order_number,
            "reason": reason, "duration_ms": int((time.time() - started) * 1000),
            "steps": log
        }

    pay_id = f"pay_demo_{uuid.uuid4().hex[:8]}"
    _mark_order_paid(db, order, payment, pay_id, method="card", actor="system")
    # One PAYMENT_SUCCESS event only: flag the synthesized capture honestly
    # on the existing row instead of logging a duplicate.
    existing = db.query(AuditEvent).filter(
        AuditEvent.event_type == "PAYMENT_SUCCESS",
        AuditEvent.related_entity_id == order.id
    ).order_by(AuditEvent.id.desc()).first()
    if existing:
        existing.event_data = {
            **(existing.event_data or {}),
            "simulated": True, "source": "demo-trigger"
        }
        db.commit()
    log.append(f"payment: captured {pay_id} (simulated capture)")
    return {
        "status": "paid", "session_id": session_id,
        "order_id": order.id, "order_number": order.order_number,
        "razorpay_order_id": rzr_order_id, "razorpay_payment_id": pay_id,
        "total_paise": totals["total_paise"], "simulated_capture": True,
        "duration_ms": int((time.time() - started) * 1000), "steps": log
    }


@router.post("/run-successful-purchase")
def run_successful_purchase(session_id: str = "demo-success", db: Session = Depends(get_db)):
    _require_demo()
    return _drive_flow(db, session_id, fail_payment=False)


@router.post("/run-payment-failure")
def run_payment_failure(session_id: str = "demo-failure", db: Session = Depends(get_db)):
    _require_demo()
    return _drive_flow(db, session_id, fail_payment=True)


@router.post("/run-upsell-scenario")
async def run_upsell_scenario(session_id: str = "demo-upsell", db: Session = Depends(get_db)):
    """Deterministic upsell: fixed product with real coverage, cart payload
    plus upsell candidates for the UI - no LLM involved."""
    _require_demo()
    from backend.services.catalog_service import CatalogService
    from backend.services.cart_service import CartService
    from backend.services.ai.tool_registry import create_tool_registry

    found, _ = CatalogService.get_products(db, query=DEMO_PRODUCT, limit=5)
    if not found:
        raise HTTPException(status_code=500, detail=f"Demo product '{DEMO_PRODUCT}' missing")
    main = next((p for p in found if p.name == DEMO_PRODUCT), found[0])

    registry = create_tool_registry()
    cart = CartService.create_cart(db, session_id, 1)
    result = await registry.execute(
        "add_to_cart",
        {"cart_id": cart.id, "product_id": main.id, "quantity": 1},
        db=db, session_id=session_id
    )

    return {
        "status": "ok", "session_id": session_id,
        "cart_id": cart.id,
        "added": main.name,
        "cart": {k: v for k, v in result.items()},
        "upsell": result.get("related_products", [])
    }
