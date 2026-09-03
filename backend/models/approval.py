from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from backend.database import Base

class Approval(Base):
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), index=True, nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    cart_id = Column(Integer, ForeignKey("carts.id", ondelete="CASCADE"), nullable=False)
    requested_amount_paise = Column(Integer, nullable=False)
    status = Column(String(20), default="pending", nullable=False)  # pending, approved, rejected, expired
    # Single-use token proving browser possession at approve/reject time.
    # Consumed (NULLed) on first use - replays fail. Nullable so pre-token
    # rows keep working until re-created.
    approval_token = Column(String(64), nullable=True, index=True)
    summary_json = Column(JSON, nullable=False)  # Full purchase breakdown
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    order = relationship("Order")
    cart = relationship("Cart")
