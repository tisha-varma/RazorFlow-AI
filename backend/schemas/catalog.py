from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class ProductVariantBase(BaseModel):
    name: str = Field(..., description="Variant name, e.g. 'UK 10'")
    sku: str = Field(..., description="Unique Stock Keeping Unit code")
    price_paise: int = Field(..., description="Variant specific price in paise")
    stock_quantity: int = Field(0, description="Available stock quantity")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Key-value variant properties")

class ProductVariantCreate(ProductVariantBase):
    pass

class ProductVariantOut(ProductVariantBase):
    id: int
    product_id: int

    class Config:
        from_attributes = True

class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    ai_description: Optional[str] = None
    category: str
    base_price_paise: int
    image_url: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    is_active: bool = True

class ProductCreate(ProductBase):
    variants: List[ProductVariantCreate] = Field(default_factory=list)

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    ai_description: Optional[str] = None
    category: Optional[str] = None
    base_price_paise: Optional[int] = None
    image_url: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None

class ProductOut(ProductBase):
    id: int
    merchant_id: int
    created_at: datetime
    variants: List[ProductVariantOut] = Field(default_factory=list)

    class Config:
        from_attributes = True

# Add related products to ProductOut
class ProductDetailOut(ProductOut):
    related_products: List[ProductOut] = Field(default_factory=list)

    class Config:
        from_attributes = True

class ProductListOut(BaseModel):
    products: List[ProductOut]
    total: int
