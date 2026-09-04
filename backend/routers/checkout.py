from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.approval import Approval
from backend.services.state_machine import state_machine, SessionState, VALID_TRANSITIONS
from backend.services.audit_service import AuditService
from backend.schemas.approval import ApprovalOut, ApprovalRequest, ApprovalActionRequest, PurchaseSummary, PurchaseSummaryItem

router = APIRouter(prefix="/checkout", tags=["Checkout"])


def _require_transition(session_id: str, target: SessionState):
    current = state_machine.get_state(session_id)
    if target not in VALID_TRANSITIONS.get(current, []):
        raise HTTPException(
            status_code=409,
            detail=f"Invalid state transition: {current.value} -> {target.value}"
        )


def _consume_approval_token(approval: Approval, req: ApprovalActionRequest):
    """Single-use proof of browser possession. Wrong/missing/consumed
    tokens are rejected before any state changes, so replays fail."""
    import hmac
    expected = approval.approval_token or ""
    if not expected or not hmac.compare_digest(expected, req.approval_token or ""):
        raise HTTPException(
            status_code=403,
            detail="Invalid or already-used approval token. Please checkout again."
        )
    approval.approval_token = None


@router.get("/summary/{cart_id}", response_model=PurchaseSummary)
def get_purchase_summary(cart_id: int, session_id: str, db: Session = Depends(get_db)):
    from backend.services.checkout_service import CheckoutService

    summary = CheckoutService.build_summary(db, session_id, cart_id)
    if "error" in summary:
        raise HTTPException(status_code=404, detail=summary["error"])

    return PurchaseSummary(
        approval_id=summary["approval_id"],
        cart_id=summary["cart_id"],
        session_id=summary["session_id"],
        items=[PurchaseSummaryItem(**item) for item in summary["items"]],
        subtotal_paise=summary["subtotal_paise"],
        upsell_total_paise=summary["upsell_total_paise"],
        total_paise=summary["total_paise"],
        status=summary["status"],
        policy_allowed=summary["policy_allowed"],
        policy_reason=summary["policy_reason"],
        policy_details=summary["policy_details"],
        approval_token=summary.get("approval_token"),
    )


@router.get("/approval/{approval_id}/summary", response_model=PurchaseSummary)
def get_approval_summary(approval_id: int, session_id: str, db: Session = Depends(get_db)):
    """Self-sufficient summary for the approval screen: only the approval
    ID and session are needed, no cart plumbing in the frontend."""
    from backend.services.checkout_service import CheckoutService

    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.session_id != session_id:
        raise HTTPException(status_code=403, detail="Session mismatch")

    summary = CheckoutService.build_summary(db, session_id, approval.cart_id)
    if "error" in summary:
        raise HTTPException(status_code=404, detail=summary["error"])
    summary["approval_id"] = approval.id
    summary["status"] = approval.status

    return PurchaseSummary(
        approval_id=summary["approval_id"],
        cart_id=summary["cart_id"],
        session_id=summary["session_id"],
        items=[PurchaseSummaryItem(**item) for item in summary["items"]],
        subtotal_paise=summary["subtotal_paise"],
        upsell_total_paise=summary["upsell_total_paise"],
        total_paise=summary["total_paise"],
        status=summary["status"],
        policy_allowed=summary["policy_allowed"],
        policy_reason=summary["policy_reason"],
        policy_details=summary["policy_details"],
        approval_token=summary.get("approval_token"),
    )


@router.post("/request-approval", response_model=ApprovalOut)
def request_approval(req: ApprovalRequest, db: Session = Depends(get_db)):
    from backend.services.checkout_service import CheckoutService

    _require_transition(req.session_id, SessionState.AWAITING_APPROVAL)

    result = CheckoutService.create_approval(db, req.session_id, req.cart_id)
    if "approval" not in result:
        if result.get("error") == "Cart not found":
            raise HTTPException(status_code=404, detail="Cart not found")
        raise HTTPException(
            status_code=400,
            detail=result.get("policy_reason") or result.get("error")
        )
    return result["approval"]


@router.post("/approve/{approval_id}", response_model=ApprovalOut)
def approve_purchase(approval_id: int, req: ApprovalActionRequest, db: Session = Depends(get_db)):
    from backend.services.checkout_service import CheckoutService
    # Cold state machine (e.g. after a restart) must not 409 a live flow:
    # recover the gate position from durable rows first.
    CheckoutService.recover_session_state(db, req.session_id)

    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.session_id != req.session_id:
        raise HTTPException(status_code=403, detail="Session mismatch")
    if approval.status != "pending":
        raise HTTPException(status_code=400, detail=f"Approval already {approval.status}")

    _consume_approval_token(approval, req)

    # The bound may have moved since this approval was created (merchant
    # tightened policy mid-session). Re-check against the CURRENT policy -
    # an approval is a snapshot, not a blank check.
    from backend.services.policy_engine import PolicyEngine
    from backend.models.policy import CommercePolicy
    policy = db.query(CommercePolicy).filter(CommercePolicy.is_active == True).first()
    if policy:
        fresh = PolicyEngine.check_purchase_policy(
            db, approval.cart_id, req.session_id, policy
        )
        if not fresh.allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Policy no longer allows this purchase: {fresh.reason} "
                "Please checkout again under the current limits.",
            )

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
    from backend.services.checkout_service import CheckoutService
    CheckoutService.recover_session_state(db, req.session_id)

    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.session_id != req.session_id:
        raise HTTPException(status_code=403, detail="Session mismatch")
    if approval.status != "pending":
        raise HTTPException(status_code=400, detail=f"Approval already {approval.status}")

    _consume_approval_token(approval, req)
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
