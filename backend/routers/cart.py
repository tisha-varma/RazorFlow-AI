from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from backend.database import get_db
from backend.schemas.cart import CartOut, CartCreate, CartItemCreate, CartItemUpdate, CartCalculateResponse
from backend.services.cart_service import CartService
from backend.models.cart import Cart, CartItem
from backend.models.product import Product

router = APIRouter(prefix="/cart", tags=["Cart"])


def cart_with_names(
    cart: Cart,
    db: Session,
    policy_allowed: Optional[bool] = None,
    policy_reason: Optional[str] = None
) -> dict:
    """Add product names to cart items."""
    # Fetch product names + images in bulk
    product_ids = [item.product_id for item in cart.items]
    products = {
        p.id: p for p in db.query(Product).filter(Product.id.in_(product_ids)).all()
    } if product_ids else {}

    items = []
    for item in cart.items:
        prod = products.get(item.product_id)
        product_name = prod.name if prod else f"Product #{item.product_id}"
        items.append({
            "id": item.id,
            "cart_id": item.cart_id,
            "product_id": item.product_id,
            "variant_id": item.variant_id,
            "quantity": item.quantity,
            "unit_price_paise": item.unit_price_paise,
            "is_upsell": item.is_upsell,
            "product_name": product_name,
            "image_url": prod.image_url if prod else None,
            "created_at": item.created_at
        })

    # Attach a fresh policy check unless the caller already ran one.
    if policy_allowed is None:
        from backend.services.cart_service import CartService
        policy = CartService.check_cart_policy(db, cart)
        policy_allowed = policy["allowed"]
        policy_reason = policy["reason"]

    return {
        "id": cart.id,
        "session_id": cart.session_id,
        "customer_id": cart.customer_id,
        "merchant_id": cart.merchant_id,
        "status": cart.status,
        "created_at": cart.created_at,
        "updated_at": cart.updated_at,
        "items": items,
        "policy_allowed": policy_allowed,
        "policy_reason": policy_reason
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_cart(req: CartCreate, db: Session = Depends(get_db)):
    cart = CartService.create_cart(db, req.session_id, req.merchant_id)
    return cart_with_names(cart, db)


@router.get("/{cart_id}")
def get_cart(cart_id: int, db: Session = Depends(get_db)):
    cart = CartService.get_cart(db, cart_id)
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    return cart_with_names(cart, db)


@router.post("/{cart_id}/items", status_code=status.HTTP_201_CREATED)
def add_item(cart_id: int, item: CartItemCreate, db: Session = Depends(get_db)):
    payload = CartService.add_item(
        db, cart_id, item.product_id, item.variant_id, item.quantity, item.is_upsell
    )
    if not payload:
        raise HTTPException(status_code=404, detail="Cart or product not found")
    return cart_with_names(
        payload["cart"], db,
        policy_allowed=payload["policy_allowed"],
        policy_reason=payload["policy_reason"]
    )


@router.put("/{cart_id}/items/{item_id}")
def update_item(cart_id: int, item_id: int, update: CartItemUpdate, db: Session = Depends(get_db)):
    payload = CartService.update_quantity(db, cart_id, item_id, update.quantity)
    if not payload:
        raise HTTPException(status_code=404, detail="Cart or item not found")
    return cart_with_names(
        payload["cart"], db,
        policy_allowed=payload["policy_allowed"],
        policy_reason=payload["policy_reason"]
    )


@router.delete("/{cart_id}/items/{item_id}")
def remove_item(cart_id: int, item_id: int, db: Session = Depends(get_db)):
    payload = CartService.remove_item(db, cart_id, item_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Cart or item not found")
    return cart_with_names(
        payload["cart"], db,
        policy_allowed=payload["policy_allowed"],
        policy_reason=payload["policy_reason"]
    )


@router.get("/{cart_id}/calculate", response_model=CartCalculateResponse)
def calculate_totals(cart_id: int, db: Session = Depends(get_db)):
    totals = CartService.calculate_totals(db, cart_id)
    if not totals:
        raise HTTPException(status_code=404, detail="Cart not found")
    return totals
