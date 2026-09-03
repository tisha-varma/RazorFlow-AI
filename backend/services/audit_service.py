import hashlib
import json

from sqlalchemy.orm import Session
from backend.models.audit import AuditEvent
from typing import Optional, Dict, Any

GENESIS_HASH = "GENESIS"


def _canonical(data: Any) -> str:
    return json.dumps(data or {}, sort_keys=True, separators=(",", ":"), default=str)


def compute_hash(prev_hash: str, event_type: str, event_data: Any,
                 actor: str, session_id: Optional[str]) -> str:
    payload = "|".join([prev_hash or GENESIS_HASH, event_type,
                        _canonical(event_data), actor or "",
                        session_id or ""])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class AuditService:
    @staticmethod
    def log_event(
        db: Session,
        event_type: str,
        actor: str,
        merchant_id: int = 1,
        session_id: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None,
        llm_reason_text: Optional[str] = None,
        policy_snapshot_id: Optional[str] = None,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[int] = None
    ) -> AuditEvent:
        last = db.query(AuditEvent).order_by(AuditEvent.id.desc()).first()
        prev = last.event_hash if last and last.event_hash else GENESIS_HASH
        event = AuditEvent(
            session_id=session_id,
            merchant_id=merchant_id,
            event_type=event_type,
            event_data=event_data or {},
            llm_reason_text=llm_reason_text,
            policy_snapshot_id=policy_snapshot_id,
            prev_hash=prev,
            event_hash=compute_hash(prev, event_type, event_data, actor, session_id),
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

    @staticmethod
    def verify_chain(db: Session) -> Dict[str, Any]:
        """Recompute every link. Returns ok / break_at_id / checked counts.
        Rows predating the chain (NULL hash) are reported, not failed — and
        `prev` is reset to GENESIS over them, mirroring exactly what
        log_event() chained off when it wrote the following row."""
        events = db.query(AuditEvent).order_by(AuditEvent.id.asc()).all()
        prev = GENESIS_HASH
        checked = 0
        legacy = 0
        for event in events:
            if not event.event_hash:
                legacy += 1
                prev = GENESIS_HASH
                continue
            expected = compute_hash(
                event.prev_hash, event.event_type,
                event.event_data, event.actor, event.session_id
            )
            if event.prev_hash != prev or expected != event.event_hash:
                return {"ok": False, "break_at_id": event.id,
                        "checked": checked, "legacy_rows": legacy}
            prev = event.event_hash
            checked += 1
        return {"ok": True, "break_at_id": None,
                "checked": checked, "legacy_rows": legacy}
