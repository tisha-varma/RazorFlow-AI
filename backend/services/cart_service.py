from sqlalchemy.orm import Session
from backend.models.cart import Cart, CartItem
from backend.models.product import Product, ProductVariant
from typing import Optional, List, Dict, Any


class CartService:
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
    ) -> Optional[Cart]:
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
        return cart

    @staticmethod
    def remove_item(db: Session, cart_id: int, item_id: int) -> Optional[Cart]:
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
        return cart

    @staticmethod
    def update_quantity(db: Session, cart_id: int, item_id: int, quantity: int) -> Optional[Cart]:
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
        return cart

    @staticmethod
    def calculate_totals(db: Session, cart_id: int) -> Optional[Dict[str, Any]]:
        cart = db.query(Cart).filter(Cart.id == cart_id).first()
        if not cart:
            return None

        items_data = []
        subtotal = 0
        for item in cart.items:
            item_total = item.unit_price_paise * item.quantity
            subtotal += item_total
            prod_name = item.product.name if item.product else f"Product #{item.product_id}"
            items_data.append({
                "item_id": item.id,
                "product_id": item.product_id,
                "product_name": prod_name,
                "quantity": item.quantity,
                "unit_price_paise": item.unit_price_paise,
                "total_paise": item_total,
                "is_upsell": item.is_upsell
            })

        return {
            "subtotal_paise": subtotal,
            "total_paise": subtotal,
            "item_count": len(cart.items),
            "items": items_data
        }
