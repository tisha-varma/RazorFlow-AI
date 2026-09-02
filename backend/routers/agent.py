import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.config import settings
from backend.schemas.agent import (
    AgentChatRequest, AgentChatResponse,
    SessionCreateRequest, SessionCreateResponse,
    SessionStateResponse, ToolCallOut
)
from backend.services.ai.llm_client import (
    GroqLLMClient, GeminiLLMClient, OllamaLLMClient, RotatingLLMClient
)
from backend.services.ai.agent import Agent
from backend.services.state_machine import state_machine, SessionState
from backend.services.cart_service import CartService

router = APIRouter(prefix="/agent", tags=["Agent"])

_agent = None


def get_agent() -> Agent:
    global _agent
    if _agent is None:
        provider = settings.LLM_PROVIDER.lower()

        if provider == "ollama":
            llm_client = OllamaLLMClient()

        elif provider == "groq":
            keys = [k.strip() for k in settings.LLM_API_KEYS.split(",") if k.strip()]
            if keys:
                clients = [GroqLLMClient(api_key=k) for k in keys]
                llm_client = RotatingLLMClient(clients)
            else:
                llm_client = GroqLLMClient()

        elif provider == "gemini":
            keys = [k.strip() for k in settings.LLM_API_KEYS.split(",") if k.strip()]
            if keys:
                clients = [GeminiLLMClient(api_key=k) for k in keys]
                llm_client = RotatingLLMClient(clients)
            else:
                llm_client = GeminiLLMClient()

        else:  # auto — try Ollama, then cloud providers
            clients = [OllamaLLMClient()]
            keys = [k.strip() for k in settings.LLM_API_KEYS.split(",") if k.strip()]
            if keys:
                clients.extend([GroqLLMClient(api_key=k) for k in keys])
                clients.extend([GeminiLLMClient(api_key=k) for k in keys])
            else:
                clients.append(GroqLLMClient())
                clients.append(GeminiLLMClient())
            llm_client = RotatingLLMClient(clients)

        _agent = Agent(llm_client)
    return _agent


@router.post("/chat", response_model=AgentChatResponse)
async def chat(req: AgentChatRequest, db: Session = Depends(get_db)):
    agent = get_agent()
    result = await agent.handle_message(
        db=db,
        session_id=req.session_id,
        message=req.message
    )
    return AgentChatResponse(
        response=result["response"],
        tool_calls=[ToolCallOut(**tc) for tc in result["tool_calls"]],
        state=result["state"],
        products=result.get("products", []),
        cart=result.get("cart")
    )


@router.post("/session", response_model=SessionCreateResponse)
def create_session(req: SessionCreateRequest = None):
    session_id = str(uuid.uuid4())
    return SessionCreateResponse(session_id=session_id, state="IDLE")


@router.get("/session/{session_id}", response_model=SessionStateResponse)
def get_session_state(session_id: str, db: Session = Depends(get_db)):
    state = state_machine.get_state(session_id)
    cart = CartService.get_active_cart_by_session(db, session_id)
    return SessionStateResponse(
        state=state.value,
        session_id=session_id,
        cart_id=cart.id if cart else None
    )
