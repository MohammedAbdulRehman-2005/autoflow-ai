"""
AutoFlow AI X — FastAPI Application Entry Point
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import sentry_sdk
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.core.rate_limit import limiter

from backend.auth.router import router as auth_router
from backend.workflow.planner.router import router as planner_router
from backend.workflow.engine.router import router as engine_router
from backend.workflow.validator.router import router as validator_router
from backend.scheduler.router import router as scheduler_router
from backend.scheduler.service import scheduler_service
from backend.core.config import get_settings
from backend.core.redis import close_redis
from backend.intent_parser.router import router as intent_router
from backend.followup_engine.router import router as followup_router
from backend.gmail.router import router as gmail_router
from backend.database.session import SessionLocal

logger = logging.getLogger(__name__)
settings = get_settings()

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.

    Startup sequence (order matters):
      1. Configure APScheduler with SQLAlchemy job store
      2. Start the scheduler (registers jobs from DB job store)
      3. Reconcile: ensure all active scheduled workflows have running jobs
         (handles cases where job store was cleared, e.g. fresh DB migration)

    Shutdown sequence:
      4. Stop APScheduler gracefully (wait=False — let current jobs finish)
      5. Close Redis connection pool
    """
    # ── STARTUP ───────────────────────────────────────────────────────────────
    logger.info(f"[Startup] Starting {settings.APP_NAME}...")

    # 1. Init APScheduler (configure, don't start yet)
    scheduler_service.init()

    # 2. Start scheduler + reconcile with DB
    db = SessionLocal()
    try:
        await scheduler_service.start(db)
        logger.info("[Startup] Scheduler initialized and reconciled with DB.")
    except Exception as e:
        logger.error(f"[Startup] Scheduler failed to start: {e}", exc_info=True)
        # Don't crash the whole app if scheduler fails — just log it
    finally:
        db.close()

    logger.info(f"[Startup] {settings.APP_NAME} is ready.")

    yield  # ← Application runs here

    # ── SHUTDOWN ──────────────────────────────────────────────────────────────
    logger.info("[Shutdown] Stopping services...")

    await scheduler_service.shutdown()
    await close_redis()

    logger.info("[Shutdown] All services stopped cleanly.")


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI App
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "AI-native workflow automation platform. "
        "Converts business requirements in natural language into "
        "fully executable, self-monitoring automation workflows."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ─────────────────────────────────────────────────────────────────────────────
# CORS
# ─────────────────────────────────────────────────────────────────────────────
# Parse ALLOWED_ORIGINS string into a list
allowed_origins = [
    origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(intent_router, prefix="/api/v1")
app.include_router(followup_router, prefix="/api/v1")
app.include_router(planner_router, prefix="/api/v1")
app.include_router(engine_router, prefix="/api/v1")
app.include_router(scheduler_router, prefix="/api/v1")
app.include_router(gmail_router, prefix="/api/v1")


# ─────────────────────────────────────────────────────────────────────────────
# System Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": "0.1.0",
        "scheduler_running": scheduler_service.is_running,
    }


@app.get("/api/v1/scheduler/status", tags=["System"])
def scheduler_status():
    """Quick check if APScheduler is running."""
    return {
        "scheduler_running": scheduler_service.is_running,
    }
