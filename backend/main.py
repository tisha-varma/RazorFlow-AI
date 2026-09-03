from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.routers import catalog, policy, cart, agent, checkout, payment

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
app.include_router(checkout.router, prefix="/api")
app.include_router(payment.router, prefix="/api")

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
