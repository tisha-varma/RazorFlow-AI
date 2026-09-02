from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class CartItemBase(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    quantity: int = Field(1, ge=1)
    is_upsell: bool = False


class CartItemCreate(CartItemBase):
    pass


class CartItemUpdate(BaseModel):
    quantity: int = Field(..., ge=1)


class CartItemOut(CartItemBase):
    id: int
    cart_id: int
    unit_price_paise: int
    product_name: str = ""
    created_at: datetime

    class Config:
        from_attributes = True


class CartOut(BaseModel):
    id: int
    session_id: str
    customer_id: str
    merchant_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    items: List[CartItemOut] = Field(default_factory=list)

    class Config:
        from_attributes = True


class CartCreate(BaseModel):
    session_id: str
    merchant_id: int = 1


class CartCalculateResponse(BaseModel):
    subtotal_paise: int
    total_paise: int
    item_count: int
    items: List[dict] = Field(default_factory=list)
