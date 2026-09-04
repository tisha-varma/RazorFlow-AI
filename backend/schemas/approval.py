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
    approval_token: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ApprovalActionRequest(BaseModel):
    session_id: str
    approval_token: str


class PurchaseSummaryItem(BaseModel):
    item_id: int
    product_id: int
    product_name: str
    category: Optional[str] = None
    quantity: int
    unit_price_paise: int
    total_paise: int
    is_upsell: bool = False
    reason: Optional[str] = None


class PurchaseSummary(BaseModel):
    approval_id: int
    cart_id: int
    session_id: str
    items: List[PurchaseSummaryItem]
    subtotal_paise: int
    upsell_total_paise: int = 0
    total_paise: int
    status: str
    policy_allowed: Optional[bool] = None
    policy_reason: Optional[str] = None
    policy_details: Optional[dict] = None
    # Single-use token for the pending approval, when one exists. Lets the
    # buyer UI render the approval gate the moment the backend mints it
    # (polling) instead of waiting ~35s for the LLM turn to finish. Scoped
    # to the session holder — the same party the chat path gives it to.
    approval_token: Optional[str] = None
