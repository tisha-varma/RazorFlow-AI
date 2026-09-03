from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from backend.database import Base

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), index=True, nullable=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(50), index=True, nullable=False)
    event_data = Column(JSON, default=dict, nullable=False)
    llm_reason_text = Column(Text, nullable=True)
    policy_snapshot_id = Column(String(120), nullable=True)
    actor = Column(String(20), nullable=False)  # user, ai, system
    timestamp = Column(DateTime, server_default=func.now(), nullable=False)
    related_entity_type = Column(String(50), nullable=True)  # order, cart, product, etc.
    related_entity_id = Column(Integer, nullable=True)

    merchant = relationship("Merchant", back_populates="audit_events")
