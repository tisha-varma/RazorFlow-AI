from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship
from backend.database import Base

class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    razorpay_key_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    products = relationship("Product", back_populates="merchant", cascade="all, delete-orphan")
    policies = relationship("CommercePolicy", back_populates="merchant", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="merchant", cascade="all, delete-orphan")
    audit_events = relationship("AuditEvent", back_populates="merchant", cascade="all, delete-orphan")
    ai_interactions = relationship("AIInteraction", back_populates="merchant", cascade="all, delete-orphan")
    revenue_metrics = relationship("RevenueMetric", back_populates="merchant", cascade="all, delete-orphan")
    uploads = relationship("CatalogUpload", back_populates="merchant", cascade="all, delete-orphan")
