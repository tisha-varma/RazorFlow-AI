from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas.cart import CartOut, CartCreate, CartItemCreate, CartItemUpdate, CartCalculateResponse
from backend.services.cart_service import CartService

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.post("", response_model=CartOut, status_code=status.HTTP_201_CREATED)
def create_cart(req: CartCreate, db: Session = Depends(get_db)):
    cart = CartService.create_cart(db, req.session_id, req.merchant_id)
    return cart


@router.get("/{cart_id}", response_model=CartOut)
def get_cart(cart_id: int, db: Session = Depends(get_db)):
    cart = CartService.get_cart(db, cart_id)
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    return cart


@router.post("/{cart_id}/items", response_model=CartOut, status_code=status.HTTP_201_CREATED)
def add_item(cart_id: int, item: CartItemCreate, db: Session = Depends(get_db)):
    cart = CartService.add_item(
        db, cart_id, item.product_id, item.variant_id, item.quantity, item.is_upsell
    )
    if not cart:
        raise HTTPException(status_code=404, detail="Cart or product not found")
    return cart


@router.put("/{cart_id}/items/{item_id}", response_model=CartOut)
def update_item(cart_id: int, item_id: int, update: CartItemUpdate, db: Session = Depends(get_db)):
    cart = CartService.update_quantity(db, cart_id, item_id, update.quantity)
    if not cart:
        raise HTTPException(status_code=404, detail="Cart or item not found")
    return cart


@router.delete("/{cart_id}/items/{item_id}", response_model=CartOut)
def remove_item(cart_id: int, item_id: int, db: Session = Depends(get_db)):
    cart = CartService.remove_item(db, cart_id, item_id)
    if not cart:
        raise HTTPException(status_code=404, detail="Cart or item not found")
    return cart


@router.get("/{cart_id}/calculate", response_model=CartCalculateResponse)
def calculate_totals(cart_id: int, db: Session = Depends(get_db)):
    totals = CartService.calculate_totals(db, cart_id)
    if not totals:
        raise HTTPException(status_code=404, detail="Cart not found")
    return totals
