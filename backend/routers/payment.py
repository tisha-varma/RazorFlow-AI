import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.config import settings
from backend.models.approval import Approval
from backend.models.cart import Cart
from backend.models.order import Order, OrderItem
from backend.models.payment import RazorpayPayment
from backend.schemas.payment import (
    PaymentConfigOut,
    CreateOrderRequest,
    CreateOrderResponse,
    VerifyPaymentRequest,
    VerifyPaymentResponse,
    WebhookResult,
)
from backend.services import payment_service
from backend.services.payment_service import PaymentConfigError, PaymentGatewayError
from backend.services.state_machine import state_machine, SessionState
from backend.services.audit_service import AuditService

router = APIRouter(prefix="/payment", tags=["Payment"])


def _set_state_best_effort(session_id: str, target: SessionState) -> None:
    if state_machine.get_state(session_id) != target:
        if state_machine.can_transition(session_id, target):
            state_machine.set_state(session_id, target)


def _mark_order_paid(
    db: Session,
    order: Order,
    payment: RazorpayPayment,
    razorpay_payment_id: str,
    method: str | None,
    actor: str = "system",
) -> Order:
    payment.razorpay_payment_id = razorpay_payment_id
    payment.status = "captured"
    payment.verified = True
    payment.method = method or payment.method
    payment.error_code = None
    payment.error_description = None

    order.status = "paid"

    cart = db.query(Cart).filter(Cart.id == order.cart_id).first()
    if cart:
        cart.status = "checked_out"

    approval = (
        db.query(Approval)
        .filter(
            Approval.cart_id == order.cart_id,
            Approval.session_id == order.session_id,
            Approval.status == "approved",
        )
        .first()
    )
    if approval:
        approval.order_id = order.id

    db.commit()
    db.refresh(order)

    _set_state_best_effort(order.session_id, SessionState.PAYMENT_SUCCESS)
    _set_state_best_effort(order.session_id, SessionState.ORDER_CONFIRMED)

    AuditService.log_event(
        db=db,
        event_type="PAYMENT_SUCCESS",
        actor=actor,
        merchant_id=order.merchant_id,
        session_id=order.session_id,
        event_data={
            "order_id": order.id,
            "order_number": order.order_number,
            "razorpay_order_id": payment.razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "amount_paise": order.total_paise,
        },
        related_entity_type="order",
        related_entity_id=order.id,
    )
    AuditService.log_event(
        db=db,
        event_type="ORDER_CONFIRMED",
        actor=actor,
        merchant_id=order.merchant_id,
        session_id=order.session_id,
        event_data={
            "order_id": order.id,
            "order_number": order.order_number,
            "total_paise": order.total_paise,
        },
        related_entity_type="order",
        related_entity_id=order.id,
    )
    return order


def _mark_order_failed(
    db: Session,
    order: Order,
    payment: RazorpayPayment | None,
    reason: str,
    actor: str = "system",
) -> None:
    # Never downgrade an already-paid order.
    if order.status == "paid":
        return
    if payment:
        payment.status = "failed"
        payment.error_description = reason
    order.status = "failed"
    db.commit()

    _set_state_best_effort(order.session_id, SessionState.PAYMENT_FAILED)

    AuditService.log_event(
        db=db,
        event_type="PAYMENT_FAILED",
        actor=actor,
        merchant_id=order.merchant_id,
        session_id=order.session_id,
        event_data={
            "order_id": order.id,
            "order_number": order.order_number,
            "reason": reason,
        },
        related_entity_type="order",
        related_entity_id=order.id,
    )


@router.get("/config", response_model=PaymentConfigOut)
def get_payment_config():
    return PaymentConfigOut(
        key_id=settings.RAZORPAY_KEY_ID,
        currency="INR",
        merchant_name="SprintGear India",
    )


@router.post("/create-order/{approval_id}", response_model=CreateOrderResponse)
def create_order(approval_id: int, req: CreateOrderRequest, db: Session = Depends(get_db)):
    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.session_id != req.session_id:
        raise HTTPException(status_code=403, detail="Session mismatch")
    if approval.status != "approved":
        raise HTTPException(
            status_code=400,
            detail=f"Approval must be approved before creating a payment order (current: {approval.status})",
        )

    cart = db.query(Cart).filter(Cart.id == approval.cart_id).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")

    summary = approval.summary_json or {}
    subtotal = int(summary.get("subtotal_paise", approval.requested_amount_paise))
    upsell_total = int(summary.get("upsell_total_paise", 0))
    total = int(approval.requested_amount_paise)

    # Idempotency: reuse an unpaid order for the same cart/total instead of
    # creating a duplicate Razorpay order on retry/double-click.
    existing = (
        db.query(Order)
        .filter(
            Order.session_id == req.session_id,
            Order.cart_id == cart.id,
            Order.status == "pending",
            Order.total_paise == total,
            Order.razorpay_order_id.isnot(None),
        )
        .first()
    )
    if existing:
        _set_state_best_effort(req.session_id, SessionState.PAYMENT_PENDING)
        return CreateOrderResponse(
            order_id=existing.id,
            order_number=existing.order_number,
            razorpay_order_id=existing.razorpay_order_id,
            amount_paise=existing.total_paise,
            currency="INR",
            key_id=settings.RAZORPAY_KEY_ID,
        )

    receipt = f"rf-a{approval.id}-{uuid.uuid4().hex[:8]}"
    try:
        rzr = payment_service.create_razorpay_order(
            total,
            receipt,
            notes={"approval_id": str(approval.id), "session_id": req.session_id},
        )
    except PaymentConfigError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except PaymentGatewayError as e:
        AuditService.log_event(
            db=db,
            event_type="PAYMENT_ORDER_FAILED",
            actor="system",
            merchant_id=cart.merchant_id,
            session_id=req.session_id,
            event_data={"approval_id": approval.id, "reason": str(e)},
            related_entity_type="approval",
            related_entity_id=approval.id,
        )
        raise HTTPException(status_code=502, detail=str(e))

    order = Order(
        order_number=f"RF-{approval.id}-{uuid.uuid4().hex[:8].upper()}",
        merchant_id=cart.merchant_id,
        customer_id=cart.customer_id,
        session_id=req.session_id,
        cart_id=cart.id,
        subtotal_paise=subtotal,
        total_paise=total,
        status="pending",
        is_ai_assisted=True,
        upsell_revenue_paise=upsell_total,
        razorpay_order_id=rzr["razorpay_order_id"],
    )
    db.add(order)
    db.flush()

    for entry in summary.get("items", []):
        db.add(OrderItem(
            order_id=order.id,
            product_id=entry.get("product_id"),
            variant_id=entry.get("variant_id"),
            product_name=entry.get("product_name", f"Product #{entry.get('product_id')}"),
            quantity=entry.get("quantity", 1),
            unit_price_paise=entry.get("unit_price_paise", 0),
            total_paise=entry.get("total_paise", 0),
            is_upsell=bool(entry.get("is_upsell", False)),
        ))

    payment = RazorpayPayment(
        order_id=order.id,
        razorpay_order_id=rzr["razorpay_order_id"],
        amount_paise=total,
        currency=rzr.get("currency", "INR"),
        status="created",
        verified=False,
        idempotency_key=receipt,
    )
    db.add(payment)
    db.commit()
    db.refresh(order)

    _set_state_best_effort(req.session_id, SessionState.PAYMENT_PENDING)

    AuditService.log_event(
        db=db,
        event_type="PAYMENT_ORDER_CREATED",
        actor="system",
        merchant_id=cart.merchant_id,
        session_id=req.session_id,
        event_data={
            "order_id": order.id,
            "order_number": order.order_number,
            "approval_id": approval.id,
            "razorpay_order_id": rzr["razorpay_order_id"],
            "amount_paise": total,
        },
        related_entity_type="order",
        related_entity_id=order.id,
    )

    return CreateOrderResponse(
        order_id=order.id,
        order_number=order.order_number,
        razorpay_order_id=rzr["razorpay_order_id"],
        amount_paise=total,
        currency="INR",
        key_id=settings.RAZORPAY_KEY_ID,
    )


@router.post("/verify", response_model=VerifyPaymentResponse)
def verify_payment(req: VerifyPaymentRequest, db: Session = Depends(get_db)):
    payment = (
        db.query(RazorpayPayment)
        .filter(RazorpayPayment.razorpay_order_id == req.razorpay_order_id)
        .first()
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment order not found")
    order = payment.order
    if order.session_id != req.session_id:
        raise HTTPException(status_code=403, detail="Session mismatch")

    # Idempotent: already reconciled (e.g. webhook arrived first).
    if payment.verified and order.status == "paid":
        return VerifyPaymentResponse(
            status="paid",
            order_id=order.id,
            order_number=order.order_number,
            total_paise=order.total_paise,
        )

    try:
        valid = payment_service.verify_payment_signature(
            payment.razorpay_order_id,  # from OUR database, never the client
            req.razorpay_payment_id,
            req.razorpay_signature,
        )
    except PaymentConfigError as e:
        raise HTTPException(status_code=503, detail=str(e))

    if not valid:
        _mark_order_failed(db, order, payment, "Signature verification failed")
        raise HTTPException(
            status_code=400,
            detail="Signature verification failed. Payment rejected - no order created.",
        )

    payment.razorpay_payment_id = req.razorpay_payment_id
    payment.razorpay_signature = req.razorpay_signature
    order = _mark_order_paid(db, order, payment, req.razorpay_payment_id, method=None)
    return VerifyPaymentResponse(
        status="paid",
        order_id=order.id,
        order_number=order.order_number,
        total_paise=order.total_paise,
    )


@router.post("/webhook", response_model=WebhookResult)
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    raw_body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing X-Razorpay-Signature header")

    try:
        valid = payment_service.verify_webhook_signature(raw_body, signature)
    except PaymentConfigError as e:
        raise HTTPException(status_code=503, detail=str(e))
    if not valid:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    import json

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook payload")

    event = payload.get("event", "")
    entity = ((payload.get("payload") or {}).get("payment") or {}).get("entity") or {}

    # Replay guard: ignore events older than 5 minutes (still 200 to stop retries).
    created_at = payload.get("created_at") or entity.get("created_at")
    if created_at and (time.time() - int(created_at) > 300):
        return WebhookResult(ok=True, detail="stale event ignored")

    if event == "payment.captured":
        return _handle_captured_webhook(db, entity)
    if event == "payment.failed":
        return _handle_failed_webhook(db, entity)
    return WebhookResult(ok=True, detail=f"event {event} ignored")


def _handle_captured_webhook(db: Session, entity: dict) -> WebhookResult:
    pay_id = entity.get("id")
    rzr_order_id = entity.get("order_id")
    if not pay_id:
        return WebhookResult(ok=True, detail="missing payment id")

    # Idempotency: an existing row with this payment id means duplicate delivery.
    existing = (
        db.query(RazorpayPayment)
        .filter(RazorpayPayment.razorpay_payment_id == pay_id)
        .first()
    )
    if existing:
        if existing.order.status == "paid":
            return WebhookResult(ok=True, detail="duplicate delivery ignored")
        _mark_order_paid(
            db, existing.order, existing, pay_id,
            method=entity.get("method"), actor="system",
        )
        return WebhookResult(ok=True, detail="reconciled to paid")

    ours = (
        db.query(RazorpayPayment)
        .filter(RazorpayPayment.razorpay_order_id == rzr_order_id)
        .first()
    )
    if not ours:
        return WebhookResult(ok=True, detail="unknown order ignored")
    if ours.order.status == "paid":
        return WebhookResult(ok=True, detail="already paid")
    _mark_order_paid(
        db, ours.order, ours, pay_id,
        method=entity.get("method"), actor="system",
    )
    return WebhookResult(ok=True, detail="reconciled to paid")


def _handle_failed_webhook(db: Session, entity: dict) -> WebhookResult:
    pay_id = entity.get("id")
    rzr_order_id = entity.get("order_id")

    target = None
    if pay_id:
        target = (
            db.query(RazorpayPayment)
            .filter(RazorpayPayment.razorpay_payment_id == pay_id)
            .first()
        )
    if not target and rzr_order_id:
        target = (
            db.query(RazorpayPayment)
            .filter(RazorpayPayment.razorpay_order_id == rzr_order_id)
            .first()
        )
    if not target:
        return WebhookResult(ok=True, detail="unknown order ignored")
    if target.order.status == "paid":
        return WebhookResult(ok=True, detail="already paid, failure ignored")

    reason = (entity.get("error_description")
              or entity.get("error_code")
              or "payment failed at gateway")
    # Record the gateway payment id for traceability, then fail without fulfilling.
    if pay_id and not target.razorpay_payment_id:
        target.razorpay_payment_id = pay_id
    _mark_order_failed(db, target.order, target, reason)
    return WebhookResult(ok=True, detail="marked failed")
