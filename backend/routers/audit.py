from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from backend.database import get_db
from backend.models.audit import AuditEvent

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("")
def list_events(
    session_id: Optional[str] = None,
    merchant_id: Optional[int] = None,
    limit: int = 200,
    db: Session = Depends(get_db)
):
    """Audit trail ordered by time. Requires a session_id or merchant_id filter."""
    if not session_id and merchant_id is None:
        raise HTTPException(
            status_code=400,
            detail="Provide session_id or merchant_id to scope the audit trail"
        )

    query = db.query(AuditEvent)
    if session_id:
        query = query.filter(AuditEvent.session_id == session_id)
    if merchant_id is not None:
        query = query.filter(AuditEvent.merchant_id == merchant_id)

    events = (
        query.order_by(AuditEvent.timestamp.asc(), AuditEvent.id.asc())
        .limit(max(1, min(limit, 500)))
        .all()
    )
    return [
        {
            "id": e.id,
            "session_id": e.session_id,
            "merchant_id": e.merchant_id,
            "event_type": e.event_type,
            "event_data": e.event_data or {},
            "llm_reason_text": e.llm_reason_text,
            "policy_snapshot_id": e.policy_snapshot_id,
            "actor": e.actor,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "related_entity_type": e.related_entity_type,
            "related_entity_id": e.related_entity_id
        }
        for e in events
    ]
