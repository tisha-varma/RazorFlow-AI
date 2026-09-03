"""Persistence hook for session state transitions (funnel analytics).

The StateMachine itself stays a pure in-memory gate. On each successful
transition it calls the recorder registered here, which appends a
SessionStateEvent row in its own short-lived session. Recording must never
break a transition, so all errors are swallowed after a console note.
"""

_session_factory = None


def configure(factory, force=False):
    """Set the DB session factory. Main app wires SessionLocal at startup;
    tests re-wire to their isolated engine (force=True)."""
    global _session_factory
    if force or _session_factory is None:
        _session_factory = factory


def record_transition(session_id: str, from_state: str, to_state: str) -> None:
    try:
        if _session_factory is None:
            from backend.database import SessionLocal
            factory = SessionLocal
        else:
            factory = _session_factory
        # Late imports: keep this module free of service-layer cycles.
        from backend.models.session_state import SessionStateEvent
        from backend.models.cart import Cart

        db = factory()
        try:
            merchant_id = None
            row = (
                db.query(Cart.merchant_id)
                .filter(Cart.session_id == session_id)
                .order_by(Cart.id.desc())
                .first()
            )
            if row:
                merchant_id = row[0]
            db.add(SessionStateEvent(
                session_id=session_id,
                from_state=from_state,
                to_state=to_state,
                merchant_id=merchant_id
            ))
            db.commit()
        finally:
            db.close()
    except Exception as e:
        print(f"[STATE-LOG] skipped recording {session_id}: {e}")
