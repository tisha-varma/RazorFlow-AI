from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from backend.database import Base

class AIInteraction(Base):
    __tablename__ = "ai_interactions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), index=True, nullable=False)
    merchant_id = Column(Integer, ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False)
    interaction_type = Column(String(50), nullable=False)  # search, recommend, upsell, cart, policy_check
    user_message = Column(Text, nullable=True)
    ai_response = Column(Text, nullable=True)
    tool_calls = Column(JSON, default=list, nullable=False)
    # Parallel array to tool_calls: [{tool_name, result}] with results
    # trimmed (lists capped) so "what did the catalog return" is answerable.
    tool_results = Column(JSON, default=list, nullable=True)
    tokens_used = Column(Integer, default=0, nullable=False)
    duration_ms = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    merchant = relationship("Merchant", back_populates="ai_interactions")
