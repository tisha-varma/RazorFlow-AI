from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.approval import Approval
from backend.models.cart import Cart
from backend.services.cart_service import CartService
from backend.services.policy_engine import PolicyEngine
from backend.services.state_machine import state_machine, SessionState, VALID_TRANSITIONS
from backend.services.audit_service import AuditService
from backend.schemas.approval import ApprovalOut, ApprovalRequest, ApprovalActionRequest, PurchaseSummary, PurchaseSummaryItem
from backend.models.policy import CommercePolicy
from backend.models.merchant import Merchant
from typing import List

router = APIRouter(prefix="/checkout", tags=["Checkout"])


def _require_transition(session_id: str, target: SessionState):
    current = state_machine.get_state(session_id)
    if target not in VALID_TRANSITIONS.get(current, []):
        raise HTTPException(
            status_code=409,
            detail=f"Invalid state transition: {current.value} -> {target.value}"
        )


@router.get("/summary/{cart_id}", response_model=PurchaseSummary)
def get_purchase_summary(cart_id: int, session_id: str, db: Session = Depends(get_db)):
    totals = CartService.calculate_totals(db, cart_id)
    if not totals:
        raise HTTPException(status_code=404, detail="Cart not found")

    policy = db.query(CommercePolicy).filter(CommercePolicy.is_active == True).first()
    policy_result = PolicyEngine.check_purchase_policy(db, cart_id, session_id, policy) if policy else None

    approval = db.query(Approval).filter(
        Approval.cart_id == cart_id,
        Approval.session_id == session_id,
        Approval.status == "pending"
    ).first()

    return PurchaseSummary(
        approval_id=approval.id if approval else 0,
        cart_id=cart_id,
        session_id=session_id,
        items=[PurchaseSummaryItem(**item) for item in totals["items"]],
        subtotal_paise=totals["subtotal_paise"],
        total_paise=totals["total_paise"],
        status=approval.status if approval else "none",
        policy_allowed=policy_result.allowed if policy_result else None,
        policy_reason=policy_result.reason if policy_result else None
    )


@router.post("/request-approval", response_model=ApprovalOut)
def request_approval(req: ApprovalRequest, db: Session = Depends(get_db)):
    _require_transition(req.session_id, SessionState.AWAITING_APPROVAL)

    totals = CartService.calculate_totals(db, req.cart_id)
    if not totals:
        raise HTTPException(status_code=404, detail="Cart not found")

    merchant = db.query(Merchant).first()
    merchant_id = merchant.id if merchant else 1

    approval = Approval(
        session_id=req.session_id,
        cart_id=req.cart_id,
        requested_amount_paise=totals["total_paise"],
        status="pending",
        summary_json={
            "items": totals["items"],
            "subtotal_paise": totals["subtotal_paise"],
            "total_paise": totals["total_paise"]
        }
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)

    state_machine.set_state(req.session_id, SessionState.AWAITING_APPROVAL)

    AuditService.log_event(
        db=db,
        event_type="PAYMENT_APPROVAL_REQUESTED",
        actor="system",
        merchant_id=merchant_id,
        session_id=req.session_id,
        event_data={
            "approval_id": approval.id,
            "cart_id": req.cart_id,
            "amount_paise": totals["total_paise"]
        },
        related_entity_type="approval",
        related_entity_id=approval.id
    )

    return approval


@router.post("/approve/{approval_id}", response_model=ApprovalOut)
def approve_purchase(approval_id: int, req: ApprovalActionRequest, db: Session = Depends(get_db)):
    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.session_id != req.session_id:
        raise HTTPException(status_code=403, detail="Session mismatch")
    if approval.status != "pending":
        raise HTTPException(status_code=400, detail=f"Approval already {approval.status}")

    _require_transition(req.session_id, SessionState.PAYMENT_PENDING)

    from datetime import datetime
    approval.status = "approved"
    approval.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(approval)

    state_machine.set_state(req.session_id, SessionState.PAYMENT_PENDING)

    AuditService.log_event(
        db=db,
        event_type="PAYMENT_APPROVED",
        actor="customer",
        merchant_id=1,
        session_id=req.session_id,
        event_data={
            "approval_id": approval.id,
            "cart_id": approval.cart_id,
            "amount_paise": approval.requested_amount_paise
        },
        related_entity_type="approval",
        related_entity_id=approval.id
    )

    return approval


@router.post("/reject/{approval_id}", response_model=ApprovalOut)
def reject_purchase(approval_id: int, req: ApprovalActionRequest, db: Session = Depends(get_db)):
    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.session_id != req.session_id:
        raise HTTPException(status_code=403, detail="Session mismatch")
    if approval.status != "pending":
        raise HTTPException(status_code=400, detail=f"Approval already {approval.status}")

    _require_transition(req.session_id, SessionState.CART_BUILDING)

    approval.status = "rejected"
    db.commit()
    db.refresh(approval)

    state_machine.set_state(req.session_id, SessionState.CART_BUILDING)

    AuditService.log_event(
        db=db,
        event_type="PAYMENT_APPROVAL_REJECTED",
        actor="customer",
        merchant_id=1,
        session_id=req.session_id,
        event_data={
            "approval_id": approval.id,
            "cart_id": approval.cart_id,
            "amount_paise": approval.requested_amount_paise
        },
        related_entity_type="approval",
        related_entity_id=approval.id
    )

    return approval
