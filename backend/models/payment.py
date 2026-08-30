from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from backend.database import Base

class RazorpayPayment(Base):
    __tablename__ = "razorpay_payments"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    razorpay_order_id = Column(String(100), index=True, nullable=False)
    razorpay_payment_id = Column(String(100), index=True, nullable=True)
    razorpay_signature = Column(String(500), nullable=True)
    amount_paise = Column(Integer, nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    status = Column(String(20), default="created", nullable=False)  # created, authorized, captured, failed, refunded
    method = Column(String(50), nullable=True)
    error_code = Column(String(100), nullable=True)
    error_description = Column(Text, nullable=True)
    verified = Column(Boolean, default=False, nullable=False)
    idempotency_key = Column(String(100), unique=True, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    order = relationship("Order", back_populates="payments")
