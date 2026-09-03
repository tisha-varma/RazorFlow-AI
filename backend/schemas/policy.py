from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class PolicyBase(BaseModel):
    max_transaction_amount_paise: int = Field(default=500000, description="Max transaction allowed in paise")
    min_transaction_amount_paise: int = Field(default=0, description="Min transaction allowed in paise (0 = no floor)")
    require_approval: bool = Field(default=True, description="Explicit approval gate flag")
    max_quantity_per_item: int = Field(default=5, description="Max quantity per individual item")
    allow_upsell: bool = Field(default=True, description="Enable upsell recommendation")
    max_upsell_amount_paise: int = Field(default=200000, description="Max upsell total in paise")
    allow_auto_retry: bool = Field(default=False, description="Retry payment on failure")
    spending_limit_paise: int = Field(default=1000000, description="Session spending limit in paise")

class PolicyCreate(PolicyBase):
    pass

class PolicyUpdate(BaseModel):
    max_transaction_amount_paise: Optional[int] = None
    min_transaction_amount_paise: Optional[int] = None
    require_approval: Optional[bool] = None
    max_quantity_per_item: Optional[int] = None
    allow_upsell: Optional[bool] = None
    max_upsell_amount_paise: Optional[int] = None
    allow_auto_retry: Optional[bool] = None
    spending_limit_paise: Optional[int] = None
    is_active: Optional[bool] = None

class PolicyOut(PolicyBase):
    id: int
    merchant_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PolicyCheckRequest(BaseModel):
    cart_id: int
    session_id: str

class PolicyCheckResponse(BaseModel):
    allowed: bool
    reason: Optional[str] = None
    policy_details: Optional[dict] = None
