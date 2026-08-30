from sqlalchemy import Column, Integer, Date, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from backend.database import Base

class RevenueMetric(Base):
    __tablename__ = "revenue_metrics"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, index=True, nullable=False)
    total_revenue_paise = Column(Integer, default=0, nullable=False)
    ai_assisted_revenue_paise = Column(Integer, default=0, nullable=False)
    upsell_revenue_paise = Column(Integer, default=0, nullable=False)
    total_orders = Column(Integer, default=0, nullable=False)
    ai_assisted_orders = Column(Integer, default=0, nullable=False)
    avg_order_value_paise = Column(Integer, default=0, nullable=False)
    conversion_rate = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    merchant = relationship("Merchant", back_populates="revenue_metrics")
