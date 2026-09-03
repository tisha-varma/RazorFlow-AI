from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ApprovalRequest(BaseModel):
    cart_id: int
    session_id: str


class ApprovalOut(BaseModel):
    id: int
    session_id: str
    cart_id: int
    requested_amount_paise: int
    status: str
    summary_json: dict
    approved_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ApprovalActionRequest(BaseModel):
    session_id: str


class PurchaseSummaryItem(BaseModel):
    item_id: int
    product_id: int
    product_name: str
    quantity: int
    unit_price_paise: int
    total_paise: int
    is_upsell: bool = False


class PurchaseSummary(BaseModel):
    approval_id: int
    cart_id: int
    session_id: str
    items: List[PurchaseSummaryItem]
    subtotal_paise: int
    total_paise: int
    status: str
    policy_allowed: Optional[bool] = None
    policy_reason: Optional[str] = None
