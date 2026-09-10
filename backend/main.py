"""
backend/main.py

Application entry-point for the Support CRM API.

Responsibilities
----------------
1. Create the FastAPI app with metadata.
2. Register CORS middleware (allow all origins for frontend development).
3. Create all database tables on startup via SQLAlchemy metadata.
4. Include routers for tickets and analytics.
5. Expose a health-check root endpoint.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.database import engine, Base
from backend.routes import tickets, analytics

# Import models so they are registered with Base.metadata before create_all.
import backend.models  # noqa: F401


# ---------------------------------------------------------------------------
# Lifespan – runs once at startup (creates tables) and once at shutdown.
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup."""
    Base.metadata.create_all(bind=engine)
    yield


# ---------------------------------------------------------------------------
# FastAPI application instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Support CRM API",
    description="Customer-support ticketing CRM with AI-powered triage.",
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS – allow all origins so the frontend can connect from any host/port.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(tickets.router)
app.include_router(analytics.router)

# Serve frontend HTML files at /app
app.mount("/app", StaticFiles(directory="frontend", html=True), name="frontend")


# ---------------------------------------------------------------------------
# Root health-check endpoint
# ---------------------------------------------------------------------------
@app.get("/", tags=["Health"])
def root():
    """Simple health-check that confirms the API is running."""
    return {"message": "Support CRM API is running"}


# ---------------------------------------------------------------------------
# Uvicorn entry-point (python -m backend.main)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
