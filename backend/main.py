from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.services.rate_limit import limit
from backend.routers import catalog, policy, cart, agent, checkout, payment, audit, dashboard, demo

app = FastAPI(
    title="RazorFlow AI Backend API",
    description="Backend API for RazorFlow AI agentic commerce dashboard and buyer interface",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(catalog.router, prefix="/api")
app.include_router(policy.router, prefix="/api")
app.include_router(cart.router, prefix="/api")
app.include_router(agent.router, prefix="/api")
# Money-adjacent surfaces are rate-limited (120/min/IP, rolling window).
app.include_router(
    checkout.router, prefix="/api",
    dependencies=[Depends(limit("checkout", 120))]
)
app.include_router(
    payment.router, prefix="/api",
    dependencies=[Depends(limit("payment", 120))]
)
app.include_router(audit.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(demo.router, prefix="/api")

@app.on_event("startup")
def _wire_state_recorder():
    # Persist transitions for funnel analytics. configure() is a no-op when
    # tests already wired their isolated engine.
    from backend.services import session_state_log
    from backend.services.state_machine import state_machine
    from backend.database import SessionLocal, engine
    from backend.services.schema_compat import ensure_sqlite_schema
    ensure_sqlite_schema(engine)
    session_state_log.configure(SessionLocal)
    state_machine.on_transition(session_state_log.record_transition)


@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "RazorFlow AI Backend API",
        "docs_url": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
