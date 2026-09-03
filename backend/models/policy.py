from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from backend.database import Base

class CommercePolicy(Base):
    __tablename__ = "commerce_policies"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False)
    max_transaction_amount_paise = Column(Integer, default=500000, nullable=False) # 5,000 INR default
    min_transaction_amount_paise = Column(Integer, default=0, nullable=False) # 0 = no floor
    require_approval = Column(Boolean, default=True, nullable=False)
    max_quantity_per_item = Column(Integer, default=5, nullable=False)
    allow_upsell = Column(Boolean, default=True, nullable=False)
    max_upsell_amount_paise = Column(Integer, default=200000, nullable=False) # 2,000 INR default
    allow_auto_retry = Column(Boolean, default=False, nullable=False)
    spending_limit_paise = Column(Integer, default=1000000, nullable=False) # 10,000 INR default
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    merchant = relationship("Merchant", back_populates="policies")
