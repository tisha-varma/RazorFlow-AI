from sqlalchemy import Column, Integer, String, DateTime, func
from backend.database import Base


class SessionStateEvent(Base):
    """Persisted log of every session state transition (funnel analytics).

    The in-memory StateMachine stays authoritative for gating; this table is
    append-only reporting so the funnel survives restarts.
    """

    __tablename__ = "session_state_events"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), index=True, nullable=False)
    from_state = Column(String(30), nullable=False)
    to_state = Column(String(30), index=True, nullable=False)
    merchant_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
