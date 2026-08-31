from enum import Enum
from typing import Optional


class SessionState(str, Enum):
    IDLE = "IDLE"
    DISCOVERING = "DISCOVERING"
    RECOMMENDING = "RECOMMENDING"
    CART_BUILDING = "CART_BUILDING"
    UPSELLING = "UPSELLING"
    POLICY_CHECK = "POLICY_CHECK"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAYMENT_SUCCESS = "PAYMENT_SUCCESS"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    ORDER_CONFIRMED = "ORDER_CONFIRMED"
    CANCELLED = "CANCELLED"


VALID_TRANSITIONS = {
    SessionState.IDLE: [SessionState.DISCOVERING],
    SessionState.DISCOVERING: [SessionState.RECOMMENDING, SessionState.IDLE, SessionState.CART_BUILDING],
    SessionState.RECOMMENDING: [SessionState.CART_BUILDING, SessionState.DISCOVERING, SessionState.UPSELLING],
    SessionState.CART_BUILDING: [SessionState.UPSELLING, SessionState.POLICY_CHECK, SessionState.RECOMMENDING],
    SessionState.UPSELLING: [SessionState.POLICY_CHECK, SessionState.CART_BUILDING],
    SessionState.POLICY_CHECK: [SessionState.AWAITING_APPROVAL, SessionState.CART_BUILDING],
    SessionState.AWAITING_APPROVAL: [SessionState.PAYMENT_PENDING, SessionState.CART_BUILDING, SessionState.CANCELLED],
    SessionState.PAYMENT_PENDING: [SessionState.PAYMENT_SUCCESS, SessionState.PAYMENT_FAILED],
    SessionState.PAYMENT_SUCCESS: [SessionState.ORDER_CONFIRMED],
    SessionState.PAYMENT_FAILED: [SessionState.CART_BUILDING, SessionState.CANCELLED],
    SessionState.ORDER_CONFIRMED: [SessionState.IDLE],
    SessionState.CANCELLED: [SessionState.IDLE],
}


class StateMachine:
    def __init__(self):
        self._sessions: dict[str, SessionState] = {}

    def get_state(self, session_id: str) -> SessionState:
        return self._sessions.get(session_id, SessionState.IDLE)

    def set_state(self, session_id: str, state: SessionState) -> bool:
        current = self.get_state(session_id)
        if state in VALID_TRANSITIONS.get(current, []):
            self._sessions[session_id] = state
            return True
        return False

    def can_transition(self, session_id: str, target: SessionState) -> bool:
        current = self.get_state(session_id)
        return target in VALID_TRANSITIONS.get(current, [])


state_machine = StateMachine()
