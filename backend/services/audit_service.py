from sqlalchemy.orm import Session
from backend.models.audit import AuditEvent
from typing import Optional, Dict, Any

class AuditService:
    @staticmethod
    def log_event(
        db: Session,
        event_type: str,
        actor: str,
        merchant_id: int = 1,
        session_id: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[int] = None
    ) -> AuditEvent:
        event = AuditEvent(
            session_id=session_id,
            merchant_id=merchant_id,
            event_type=event_type,
            event_data=event_data or {},
            actor=actor,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        
        # Log to server console
        print(f"[AUDIT] [{actor.upper()}] {event_type} - Session: {session_id} - Data: {event_data}")
        return event
