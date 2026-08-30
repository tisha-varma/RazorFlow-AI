from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from backend.database import Base

class CatalogUpload(Base):
    __tablename__ = "catalog_uploads"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    status = Column(String(20), default="pending", nullable=False)  # pending, processing, completed, failed
    total_rows = Column(Integer, default=0, nullable=False)
    processed_rows = Column(Integer, default=0, nullable=False)
    errors = Column(JSON, default=list, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    merchant = relationship("Merchant", back_populates="uploads")
