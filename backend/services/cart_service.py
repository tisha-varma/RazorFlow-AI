from sqlalchemy.orm import Session
from backend.models.cart import Cart, CartItem
from backend.models.product import Product, ProductVariant
from backend.models.policy import CommercePolicy
from backend.services.policy_engine import PolicyEngine
from backend.services.audit_service import AuditService
from typing import Optional, List, Dict, Any


class CartService:
    @staticmethod
    def check_cart_policy(db: Session, cart: Cart) -> Dict[str, Any]:
        """Run the active commerce policy against a cart. Internal only."""
        policy = db.query(CommercePolicy).filter(CommercePolicy.is_active == True).first()
        if not policy:
            return {
                "allowed": True,
                "reason": "No active commerce policy - defaulting to allow",
                "details": {}
            }
        result = PolicyEngine.check_purchase_policy(db, cart.id, cart.session_id, policy)
        return {
            "allowed": result.allowed,
            "reason": result.reason,
            "details": result.policy_details
        }

    @staticmethod
    def _mutation_payload(db: Session, cart: Cart) -> Dict[str, Any]:
        """Build the return payload for a cart mutation.

        Every mutation automatically runs the policy check so the caller
        (LLM tool handler or REST endpoint) sees allowed/blocked + reason
        without a separate policy round trip.
        """
        totals = CartService.calculate_totals(db, cart.id)
        policy = CartService.check_cart_policy(db, cart)

        details = policy["details"] or {}
        policy_snapshot_id = details.get("policy_snapshot_id")
        AuditService.log_event(
            db=db,
            event_type="POLICY_CHECK_PASSED" if policy["allowed"] else "POLICY_CHECK_FAILED",
            actor="system",
            merchant_id=cart.merchant_id,
            session_id=cart.session_id,
            event_data={
                "cart_id": cart.id,
                "allowed": policy["allowed"],
                "reason": policy["reason"],
                "cart_total_paise": totals["total_paise"] if totals else 0,
                "max_transaction_paise": details.get("max_transaction_paise") or details.get("max_transaction"),
                "spending_limit_paise": details.get("spending_limit_paise"),
                "remaining_paise": details.get("remaining_budget"),
                "policy_snapshot_id": policy_snapshot_id,
                "policy_snapshot": details
            },
            policy_snapshot_id=policy_snapshot_id,
            related_entity_type="cart",
            related_entity_id=cart.id
        )

        return {
            "cart": cart,
            "cart_id": cart.id,
            "status": cart.status,
            "item_count": totals["item_count"] if totals else 0,
            "total_paise": totals["total_paise"] if totals else 0,
            "items": totals["items"] if totals else [],
            "policy_allowed": policy["allowed"],
            "policy_reason": policy["reason"],
            "policy_details": policy["details"]
        }
    @staticmethod
    def create_cart(db: Session, session_id: str, merchant_id: int = 1) -> Cart:
        cart = Cart(
            session_id=session_id,
            merchant_id=merchant_id,
            status="active"
        )
        db.add(cart)
        db.commit()
        db.refresh(cart)
        return cart

    @staticmethod
    def get_cart(db: Session, cart_id: int) -> Optional[Cart]:
        return db.query(Cart).filter(Cart.id == cart_id).first()

    @staticmethod
    def get_active_cart_by_session(db: Session, session_id: str) -> Optional[Cart]:
        return db.query(Cart).filter(
            Cart.session_id == session_id,
            Cart.status == "active"
        ).first()

    @staticmethod
    def add_item(
        db: Session,
        cart_id: int,
        product_id: int,
        variant_id: Optional[int] = None,
        quantity: int = 1,
        is_upsell: bool = False
    ) -> Optional[Dict[str, Any]]:
        cart = db.query(Cart).filter(Cart.id == cart_id).first()
        if not cart:
            return None

        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return None

        # Determine price: variant price or base price
        if variant_id:
            variant = db.query(ProductVariant).filter(
                ProductVariant.id == variant_id,
                ProductVariant.product_id == product_id
            ).first()
            if not variant:
                return None
            unit_price = variant.price_paise
        else:
            unit_price = product.base_price_paise

        # Upsell inference (backup for the LLM flag): an item that complements
        # something already in the cart is upsell revenue by definition.
        # Explicit is_upsell=True is always respected.
        if not is_upsell:
            from backend.services.catalog_service import CatalogService
            other_ids = {
                i.product_id for i in cart.items if i.product_id != product_id
            }
            for pid in other_ids:
                related, _ = CatalogService.get_related_products_with_source(db, pid)
                if product_id in {r.id for r in related}:
                    is_upsell = True
                    break

        # Check if item already exists in cart (same product + variant)
        existing_item = db.query(CartItem).filter(
            CartItem.cart_id == cart_id,
            CartItem.product_id == product_id,
            CartItem.variant_id == variant_id
        ).first()

        if existing_item:
            existing_item.quantity += quantity
        else:
            item = CartItem(
                cart_id=cart_id,
                product_id=product_id,
                variant_id=variant_id,
                quantity=quantity,
                unit_price_paise=unit_price,
                is_upsell=is_upsell
            )
            db.add(item)

        db.commit()
        db.refresh(cart)
        return CartService._mutation_payload(db, cart)

    @staticmethod
    def find_item(
        db: Session,
        cart_id: int,
        item_id: Optional[int] = None,
        product_id: Optional[int] = None,
        product_name: Optional[str] = None
    ) -> Optional[CartItem]:
        """Resolve a cart item by id, product id, or fuzzy product name.

        The LLM never knows item_ids reliably, so callers may pass what the
        customer actually said. First match wins.
        """
        if item_id:
            item = db.query(CartItem).filter(
                CartItem.id == item_id,
                CartItem.cart_id == cart_id
            ).first()
            if item:
                return item
        if product_id:
            item = db.query(CartItem).filter(
                CartItem.cart_id == cart_id,
                CartItem.product_id == product_id
            ).first()
            if item:
                return item
        if product_name and product_name.strip():
            needle = f"%{product_name.strip()}%"
            item = db.query(CartItem).join(
                Product, Product.id == CartItem.product_id
            ).filter(
                CartItem.cart_id == cart_id,
                Product.name.ilike(needle)
            ).first()
            if item:
                return item
        return None

    @staticmethod
    def remove_item(db: Session, cart_id: int, item_id: int) -> Optional[Dict[str, Any]]:
        cart = db.query(Cart).filter(Cart.id == cart_id).first()
        if not cart:
            return None

        item = db.query(CartItem).filter(
            CartItem.id == item_id,
            CartItem.cart_id == cart_id
        ).first()
        if not item:
            return None

        db.delete(item)
        db.commit()
        db.refresh(cart)
        return CartService._mutation_payload(db, cart)

    @staticmethod
    def update_quantity(db: Session, cart_id: int, item_id: int, quantity: int) -> Optional[Dict[str, Any]]:
        cart = db.query(Cart).filter(Cart.id == cart_id).first()
        if not cart:
            return None

        item = db.query(CartItem).filter(
            CartItem.id == item_id,
            CartItem.cart_id == cart_id
        ).first()
        if not item:
            return None

        item.quantity = quantity
        db.commit()
        db.refresh(cart)
        return CartService._mutation_payload(db, cart)

    @staticmethod
    def calculate_totals(db: Session, cart_id: int) -> Optional[Dict[str, Any]]:
        cart = db.query(Cart).filter(Cart.id == cart_id).first()
        if not cart:
            return None

        items_data = []
        subtotal = 0
        upsell_total = 0
        for item in cart.items:
            item_total = item.unit_price_paise * item.quantity
            subtotal += item_total
            if item.is_upsell:
                upsell_total += item_total
            prod_name = item.product.name if item.product else f"Product #{item.product_id}"
            items_data.append({
                "item_id": item.id,
                "product_id": item.product_id,
                "variant_id": item.variant_id,
                "product_name": prod_name,
                "quantity": item.quantity,
                "unit_price_paise": item.unit_price_paise,
                "total_paise": item_total,
                "is_upsell": item.is_upsell
            })

        return {
            "subtotal_paise": subtotal,
            "upsell_total_paise": upsell_total,
            "total_paise": subtotal,
            "item_count": len(cart.items),
            "items": items_data
        }
