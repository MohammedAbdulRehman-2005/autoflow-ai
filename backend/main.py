"""
AutoFlow AI X — FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.auth.router import router as auth_router
from backend.workflow.planner.router import router as planner_router
from backend.core.config import get_settings
from backend.core.redis import close_redis
from backend.intent_parser.router import router as intent_router
from backend.followup_engine.router import router as followup_router
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup / shutdown lifecycle manager.
    - Startup: nothing needed (Redis client is lazy-initialized on first request)
    - Shutdown: gracefully close the Redis connection pool
    """
    yield
    await close_redis()


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-native workflow automation platform",
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — adjust origins for production
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth_router, prefix="/api/v1")
app.include_router(intent_router, prefix="/api/v1")
app.include_router(followup_router, prefix="/api/v1")
app.include_router(planner_router, prefix="/api/v1")



# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}
