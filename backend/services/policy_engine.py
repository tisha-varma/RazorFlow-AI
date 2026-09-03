from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.models.policy import CommercePolicy
from backend.models.cart import Cart
from backend.models.order import Order
from typing import Optional, Dict, Any

class PolicyResult:
    def __init__(self, allowed: bool, reason: Optional[str] = None, policy_details: Optional[Dict[str, Any]] = None):
        self.allowed = allowed
        self.reason = reason
        self.policy_details = policy_details or {}

    def to_dict(self):
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "policy_details": self.policy_details
        }

class PolicyEngine:
    @staticmethod
    def build_policy_snapshot(policy: CommercePolicy) -> Dict[str, Any]:
        updated_at = policy.updated_at.isoformat() if policy.updated_at else "unversioned"
        snapshot_id = f"policy-{policy.id}-{updated_at}"
        return {
            "policy_id": policy.id,
            "policy_snapshot_id": snapshot_id,
            "merchant_id": policy.merchant_id,
            "max_transaction_paise": policy.max_transaction_amount_paise,
            "spending_limit_paise": policy.spending_limit_paise,
            "max_quantity_per_item": policy.max_quantity_per_item,
            "allow_upsell": policy.allow_upsell,
            "max_upsell_amount_paise": policy.max_upsell_amount_paise,
            "allow_auto_retry": policy.allow_auto_retry,
            "approval_required": policy.require_approval,
            "is_active": policy.is_active,
            "updated_at": updated_at,
        }

    @staticmethod
    def get_session_total_spent(db: Session, session_id: str) -> int:
        """Sum of total paise spent on completed (paid) orders in the current session"""
        result = db.query(func.sum(Order.total_paise)).filter(
            Order.session_id == session_id,
            Order.status == "paid"
        ).scalar()
        return result or 0

    @staticmethod
    def check_purchase_policy(db: Session, cart_id: int, session_id: str, policy: CommercePolicy) -> PolicyResult:
        # Fetch cart
        cart = db.query(Cart).filter(Cart.id == cart_id).first()
        if not cart:
            return PolicyResult(allowed=False, reason=f"Cart with ID {cart_id} not found")
        
        if not cart.items:
            return PolicyResult(allowed=False, reason="Cart is empty")

        # Calculate cart total
        cart_total = sum(item.unit_price_paise * item.quantity for item in cart.items)

        session_spent = PolicyEngine.get_session_total_spent(db, session_id)
        upsell_total = sum(
            item.unit_price_paise * item.quantity
            for item in cart.items if item.is_upsell
        )
        policy_details = {
            **PolicyEngine.build_policy_snapshot(policy),
            "cart_total_paise": cart_total,
            "session_spent_paise": session_spent,
            "upsell_total_paise": upsell_total,
            "remaining_budget": policy.spending_limit_paise - session_spent - cart_total,
        }

        # 1. Cart total vs max transaction amount
        if cart_total > policy.max_transaction_amount_paise:
            return PolicyResult(
                allowed=False,
                reason=f"Cart total ₹{cart_total/100:.2f} exceeds maximum transaction limit of ₹{policy.max_transaction_amount_paise/100:.2f}",
                policy_details=policy_details
            )

        # 2. Individual item quantities and names
        for item in cart.items:
            if item.quantity > policy.max_quantity_per_item:
                prod_name = item.product.name if item.product else f"Product #{item.product_id}"
                return PolicyResult(
                    allowed=False,
                    reason=f"{prod_name}: quantity {item.quantity} exceeds maximum of {policy.max_quantity_per_item} per item",
                    policy_details=policy_details
                )

        # 3. Session spending limit
        if session_spent + cart_total > policy.spending_limit_paise:
            remaining = max(0, policy.spending_limit_paise - session_spent)
            return PolicyResult(
                allowed=False,
                reason=f"This purchase of ₹{cart_total/100:.2f} would exceed session spending limit of ₹{policy.spending_limit_paise/100:.2f}. Remaining budget: ₹{remaining/100:.2f}",
                policy_details=policy_details
            )

        # 4. Upsell amount check
        if upsell_total > policy.max_upsell_amount_paise:
            return PolicyResult(
                allowed=False,
                reason=f"Upsell total ₹{upsell_total/100:.2f} exceeds maximum upsell limit of ₹{policy.max_upsell_amount_paise/100:.2f}",
                policy_details=policy_details
            )

        # All checks passed
        return PolicyResult(
            allowed=True,
            policy_details={
                **policy_details,
                # Backward-compatible aliases used by existing API/UI code.
                "max_transaction": policy.max_transaction_amount_paise,
                "cart_total": cart_total,
                "session_spent": session_spent,
            }
        )
