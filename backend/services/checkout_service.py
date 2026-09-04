import uuid

from sqlalchemy.orm import Session
from typing import Dict, Any

from backend.models.approval import Approval
from backend.models.order import Order
from backend.models.policy import CommercePolicy
from backend.models.merchant import Merchant
from backend.services.cart_service import CartService
from backend.services.policy_engine import PolicyEngine
from backend.services.state_machine import state_machine, SessionState
from backend.services.audit_service import AuditService


class CheckoutService:
    """Deterministic checkout operations.

    The LLM never calls these directly. The agent orchestrator invokes
    create_approval() when checkout intent is detected, after the policy
    check (which already runs automatically on every cart mutation) passes.
    """

    @staticmethod
    def _advance_to_awaiting_approval(session_id: str) -> None:
        """Walk the state graph toward AWAITING_APPROVAL.

        Normal path: CART_BUILDING/UPSELLING -> POLICY_CHECK -> AWAITING_APPROVAL.
        Falls back to a direct assignment so the approval gate still engages
        even if the session is in an unexpected state.
        """
        for _ in range(4):
            current = state_machine.get_state(session_id)
            if current == SessionState.AWAITING_APPROVAL:
                return
            if current == SessionState.POLICY_CHECK:
                if state_machine.set_state(session_id, SessionState.AWAITING_APPROVAL):
                    return
                break
            if state_machine.can_transition(session_id, SessionState.POLICY_CHECK):
                state_machine.set_state(session_id, SessionState.POLICY_CHECK)
            elif state_machine.can_transition(session_id, SessionState.CART_BUILDING):
                state_machine.set_state(session_id, SessionState.CART_BUILDING)
            else:
                break
        # Fallback: guarantee the gate engages.
        state_machine._sessions[session_id] = SessionState.AWAITING_APPROVAL

    @staticmethod
    def recover_session_state(db: Session, session_id: str) -> SessionState | None:
        """Restore in-memory state from durable rows after a restart.

        The state machine is volatile; approvals and orders are not. When the
        machine has no record (IDLE) but the DB shows a live gate, reset to
        the matching state so strict transitions (approve/reject) don't 409
        on a flow that is actually mid-flight. Returns the recovered state,
        or None when there was nothing to recover.
        """
        if state_machine.get_state(session_id) != SessionState.IDLE:
            return None
        pending = db.query(Approval).filter(
            Approval.session_id == session_id,
            Approval.status == "pending"
        ).first()
        if pending:
            state_machine._sessions[session_id] = SessionState.AWAITING_APPROVAL
            return SessionState.AWAITING_APPROVAL
        approved_unpaid = (
            db.query(Approval.id)
            .join(Order, Order.id == Approval.order_id)
            .filter(
                Approval.session_id == session_id,
                Approval.status == "approved",
                Order.status != "paid"
            )
            .first()
        )
        if approved_unpaid:
            state_machine._sessions[session_id] = SessionState.PAYMENT_PENDING
            return SessionState.PAYMENT_PENDING
        return None

    @staticmethod
    def create_approval(db: Session, session_id: str, cart_id: int) -> Dict[str, Any]:
        """Create a pending Approval for a cart, deterministically.

        Returns {"approval": Approval, ...} on success, or
        {"error": ..., "policy_allowed": False, "policy_reason": ...} when
        the purchase cannot proceed (missing/empty cart, policy block).
        Reuses an existing pending approval for the same session+cart.
        """
        totals = CartService.calculate_totals(db, cart_id)
        if not totals:
            return {"error": "Cart not found", "policy_allowed": False, "policy_reason": "Cart not found"}
        if totals["item_count"] == 0:
            return {"error": "Cart is empty", "policy_allowed": False, "policy_reason": "Cart is empty"}

        policy = db.query(CommercePolicy).filter(CommercePolicy.is_active == True).first()
        if policy:
            policy_result = PolicyEngine.check_purchase_policy(db, cart_id, session_id, policy)
            policy_snapshot_id = policy_result.policy_details.get("policy_snapshot_id")
            if not policy_result.allowed:
                state_machine.set_state(session_id, SessionState.POLICY_CHECK)
                AuditService.log_event(
                    db=db,
                    event_type="POLICY_CHECK_FAILED",
                    actor="system",
                    merchant_id=policy.merchant_id,
                    session_id=session_id,
                    event_data={
                        "cart_id": cart_id,
                        "allowed": False,
                        "reason": policy_result.reason,
                        "cart_total_paise": totals["total_paise"],
                        "max_transaction_paise": policy_result.policy_details.get("max_transaction_paise"),
                        "spending_limit_paise": policy_result.policy_details.get("spending_limit_paise"),
                        "remaining_paise": policy_result.policy_details.get("remaining_budget"),
                        "policy_snapshot_id": policy_snapshot_id,
                        "policy_snapshot": policy_result.policy_details
                    },
                    policy_snapshot_id=policy_snapshot_id,
                    related_entity_type="cart",
                    related_entity_id=cart_id
                )
                return {
                    "error": policy_result.reason,
                    "policy_allowed": False,
                    "policy_reason": policy_result.reason
                }
            AuditService.log_event(
                db=db,
                event_type="POLICY_CHECK_PASSED",
                actor="system",
                merchant_id=policy.merchant_id,
                session_id=session_id,
                event_data={
                    "cart_id": cart_id,
                    "allowed": True,
                    "reason": None,
                    "cart_total_paise": totals["total_paise"],
                    "max_transaction_paise": policy_result.policy_details.get("max_transaction_paise"),
                    "spending_limit_paise": policy_result.policy_details.get("spending_limit_paise"),
                    "remaining_paise": policy_result.policy_details.get("remaining_budget"),
                    "policy_snapshot_id": policy_snapshot_id,
                    "policy_snapshot": policy_result.policy_details
                },
                policy_snapshot_id=policy_snapshot_id,
                related_entity_type="cart",
                related_entity_id=cart_id
            )

        # Reuse an existing pending approval ONLY if it still matches the
        # live cart total. A mutated cart (e.g. upsell added after the first
        # checkout intent) must never pay a frozen stale amount.
        existing = db.query(Approval).filter(
            Approval.cart_id == cart_id,
            Approval.session_id == session_id,
            Approval.status == "pending"
        ).first()
        if existing:
            if existing.requested_amount_paise != totals["total_paise"]:
                existing.status = "expired"
                db.commit()
                _merchant = db.query(Merchant).first()
                AuditService.log_event(
                    db=db,
                    event_type="PAYMENT_APPROVAL_EXPIRED",
                    actor="system",
                    merchant_id=_merchant.id if _merchant else 1,
                    session_id=session_id,
                    event_data={
                        "approval_id": existing.id,
                        "cart_id": cart_id,
                        "old_amount_paise": existing.requested_amount_paise,
                        "new_amount_paise": totals["total_paise"],
                        "reason": "cart changed since approval was created"
                    },
                    related_entity_type="approval",
                    related_entity_id=existing.id
                )
            else:
                CheckoutService._advance_to_awaiting_approval(session_id)
                return {
                    "approval": existing,
                    "reused": True,
                    "policy_allowed": True,
                    "policy_reason": None,
                    "totals": totals
                }

        merchant = db.query(Merchant).first()
        merchant_id = merchant.id if merchant else 1

        # Policy snapshot: reconstructing "what limit was in force" must not
        # depend on the merchant's CURRENT policy row, which can change.
        policy_snapshot = None
        if policy:
            policy_snapshot = {
                "policy_id": policy.id,
                "max_transaction_paise": policy.max_transaction_amount_paise,
                "min_transaction_paise": policy.min_transaction_amount_paise or 0,
                "spending_limit_paise": policy.spending_limit_paise,
                "max_quantity_per_item": policy.max_quantity_per_item,
                "max_upsell_amount_paise": policy.max_upsell_amount_paise,
                "require_approval": policy.require_approval
            }
        approval = Approval(
            session_id=session_id,
            cart_id=cart_id,
            requested_amount_paise=totals["total_paise"],
            status="pending",
            approval_token=uuid.uuid4().hex,
            summary_json={
                "items": totals["items"],
                "subtotal_paise": totals["subtotal_paise"],
                "upsell_total_paise": totals.get("upsell_total_paise", 0),
                "total_paise": totals["total_paise"],
                "policy_snapshot": policy_snapshot
            }
        )
        db.add(approval)
        db.commit()
        db.refresh(approval)

        CheckoutService._advance_to_awaiting_approval(session_id)

        AuditService.log_event(
            db=db,
            event_type="PAYMENT_APPROVAL_REQUESTED",
            actor="system",
            merchant_id=merchant_id,
            session_id=session_id,
            event_data={
                "approval_id": approval.id,
                "cart_id": cart_id,
                "amount_paise": totals["total_paise"]
            },
            related_entity_type="approval",
            related_entity_id=approval.id
        )

        return {
            "approval": approval,
            "reused": False,
            "policy_allowed": True,
            "policy_reason": None,
            "totals": totals
        }

    @staticmethod
    def build_summary(db: Session, session_id: str, cart_id: int) -> Dict[str, Any]:
        """Build the full explainability payload for the approval screen.

        Itemized cart (with categories and upsell pairing reasons), totals,
        and the complete policy context (limits, spend, remaining budget).
        Returns {"error": ...} when the cart is missing.
        """
        from backend.services.catalog_service import CatalogService

        totals = CartService.calculate_totals(db, cart_id)
        if not totals:
            return {"error": "Cart not found"}

        policy = db.query(CommercePolicy).filter(CommercePolicy.is_active == True).first()
        policy_result = (
            PolicyEngine.check_purchase_policy(db, cart_id, session_id, policy)
            if policy else None
        )

        # Upsell pairing reasons, derived from catalog relations: an upsell
        # item U paired with main item M reads "Pairs with <M name>".
        # Tag-fallback matches read "Commonly bought with <category>",
        # mirroring the card reasoning text from the recommend flow.
        main_ids = [i["product_id"] for i in totals["items"] if not i["is_upsell"]]
        main_info: Dict[int, Dict[str, Any]] = {}
        for pid in main_ids:
            prod = CatalogService.get_product_by_id(db, pid)
            if prod:
                main_info[pid] = {
                    "name": prod.name,
                    "category": prod.category,
                    "tags": set(prod.tags or []),
                    "explicit": {r.id for r in prod.related_products}
                }

        items = []
        for entry in totals["items"]:
            prod = CatalogService.get_product_by_id(db, entry["product_id"])
            reason = None
            if entry["is_upsell"]:
                reason = "Upsell add-on"
                upsell_tags = set(prod.tags or []) if prod else set()
                for pid, info in main_info.items():
                    if entry["product_id"] in info["explicit"]:
                        reason = f"Pairs with {info['name']}"
                        break
                else:
                    for pid, info in main_info.items():
                        shared = sorted(info["tags"] & upsell_tags)[:2]
                        if shared:
                            reason = (
                                f"Commonly bought with {info['category']} "
                                f"— matches {', '.join(shared)}"
                            )
                            break
            items.append({
                **entry,
                "category": prod.category if prod else None,
                "reason": reason
            })

        approval = db.query(Approval).filter(
            Approval.cart_id == cart_id,
            Approval.session_id == session_id,
            Approval.status == "pending"
        ).first()

        return {
            "approval_id": approval.id if approval else 0,
            "cart_id": cart_id,
            "session_id": session_id,
            "items": items,
            "subtotal_paise": totals["subtotal_paise"],
            "upsell_total_paise": totals.get("upsell_total_paise", 0),
            "total_paise": totals["total_paise"],
            "status": approval.status if approval else "none",
            "policy_allowed": policy_result.allowed if policy_result else None,
            "policy_reason": policy_result.reason if policy_result else None,
            "policy_details": policy_result.policy_details if policy_result else None,
            # Only live (unconsumed) tokens unlock the gate; a consumed/None
            # token means "checkout again", never auto-show.
            "approval_token": approval.approval_token if approval else None,
        }
