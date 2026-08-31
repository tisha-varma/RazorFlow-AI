from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import CommercePolicy, Merchant
from backend.schemas.policy import PolicyCreate, PolicyUpdate, PolicyOut, PolicyCheckRequest, PolicyCheckResponse
from backend.services.policy_engine import PolicyEngine
from backend.services.audit_service import AuditService

router = APIRouter(prefix="/policy", tags=["Policy"])

@router.get("", response_model=PolicyOut)
def get_active_policy(
    merchant_id: int = Query(1, description="Hardcoded merchant ID for demo"),
    db: Session = Depends(get_db)
):
    policy = db.query(CommercePolicy).filter(
        CommercePolicy.merchant_id == merchant_id,
        CommercePolicy.is_active == True
    ).first()
    
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active commerce policy found. Please run setup first."
        )
    return policy

@router.post("", response_model=PolicyOut, status_code=status.HTTP_201_CREATED)
def create_policy(
    policy_data: PolicyCreate,
    merchant_id: int = Query(1, description="Hardcoded merchant ID for demo"),
    db: Session = Depends(get_db)
):
    # Verify merchant exists
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Merchant not found"
        )
        
    # Check if a policy already exists
    existing = db.query(CommercePolicy).filter(
        CommercePolicy.merchant_id == merchant_id,
        CommercePolicy.is_active == True
    ).first()
    
    if existing:
        # Instead of creating new, redirect or raise conflict, or let them update it
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Policy already exists. Use PUT to modify it."
        )

    policy = CommercePolicy(
        merchant_id=merchant_id,
        max_transaction_amount_paise=policy_data.max_transaction_amount_paise,
        require_approval=policy_data.require_approval,
        max_quantity_per_item=policy_data.max_quantity_per_item,
        allow_upsell=policy_data.allow_upsell,
        max_upsell_amount_paise=policy_data.max_upsell_amount_paise,
        allow_auto_retry=policy_data.allow_auto_retry,
        spending_limit_paise=policy_data.spending_limit_paise,
        is_active=True
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)

    AuditService.log_event(
        db=db,
        event_type="POLICY_CHANGED",
        actor="merchant",
        merchant_id=merchant_id,
        event_data={
            "action": "created",
            "policy": {
                "max_txn": policy.max_transaction_amount_paise,
                "session_limit": policy.spending_limit_paise,
                "require_approval": policy.require_approval
            }
        },
        related_entity_type="policy",
        related_entity_id=policy.id
    )

    return policy

@router.put("/{id}", response_model=PolicyOut)
def update_policy(
    id: int,
    policy_data: PolicyUpdate,
    db: Session = Depends(get_db)
):
    policy = db.query(CommercePolicy).filter(CommercePolicy.id == id).first()
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy with ID {id} not found"
        )

    # Collect old values for auditing
    old_values = {}
    changes = {}
    update_dict = policy_data.model_dump(exclude_unset=True)

    for field, new_val in update_dict.items():
        old_val = getattr(policy, field)
        if old_val != new_val:
            old_values[field] = old_val
            changes[field] = {"old": old_val, "new": new_val}
            setattr(policy, field, new_val)

    if changes:
        db.commit()
        db.refresh(policy)
        # Log policy changed event to audit trail
        AuditService.log_event(
            db=db,
            event_type="POLICY_CHANGED",
            actor="merchant",
            merchant_id=policy.merchant_id,
            event_data={
                "action": "updated",
                "changes": changes
            },
            related_entity_type="policy",
            related_entity_id=policy.id
        )

    return policy

@router.post("/check", response_model=PolicyCheckResponse)
def check_policy(
    req: PolicyCheckRequest,
    db: Session = Depends(get_db)
):
    # Fetch active policy
    policy = db.query(CommercePolicy).filter(
        CommercePolicy.is_active == True
    ).first()
    
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active commerce policy found"
        )
        
    result = PolicyEngine.check_purchase_policy(db, req.cart_id, req.session_id, policy)
    
    # Log audit event
    AuditService.log_event(
        db=db,
        event_type="POLICY_CHECK_PASSED" if result.allowed else "POLICY_CHECK_FAILED",
        actor="system",
        merchant_id=policy.merchant_id,
        session_id=req.session_id,
        event_data={
            "cart_id": req.cart_id,
            "allowed": result.allowed,
            "reason": result.reason,
            "details": result.policy_details
        },
        related_entity_type="cart",
        related_entity_id=req.cart_id
    )

    return result.to_dict()
