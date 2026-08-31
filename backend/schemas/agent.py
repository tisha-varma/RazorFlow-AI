from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime


class AgentChatRequest(BaseModel):
    session_id: str
    message: str


class ToolCallOut(BaseModel):
    tool_name: str
    arguments: dict
    result: Any = None


class AgentChatResponse(BaseModel):
    response: str
    tool_calls: List[ToolCallOut] = Field(default_factory=list)
    state: str
    products: List[dict] = Field(default_factory=list)
    cart: Optional[dict] = None


class SessionStateResponse(BaseModel):
    state: str
    session_id: str
    cart_id: Optional[int] = None
    messages: List[dict] = Field(default_factory=list)


class SessionCreateRequest(BaseModel):
    spending_limit_paise: Optional[int] = None


class SessionCreateResponse(BaseModel):
    session_id: str
    state: str = "IDLE"
