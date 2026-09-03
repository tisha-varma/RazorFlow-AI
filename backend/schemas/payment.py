from pydantic import BaseModel, Field
from typing import Optional


class PaymentConfigOut(BaseModel):
    key_id: str
    currency: str = "INR"
    merchant_name: str = "SprintGear India"


class CreateOrderRequest(BaseModel):
    session_id: str


class CreateOrderResponse(BaseModel):
    order_id: int
    order_number: str
    razorpay_order_id: str
    amount_paise: int
    currency: str = "INR"
    key_id: str


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    session_id: str


class VerifyPaymentResponse(BaseModel):
    status: str
    order_id: int
    order_number: str
    total_paise: int
    razorpay_payment_id: str | None = None


class WebhookResult(BaseModel):
    ok: bool = True
    detail: Optional[str] = None
