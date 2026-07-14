"""
AutoFlow AI X — FastAPI Application Entry Point
"""
import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import sentry_sdk
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from backend.routes.transcribe import router as transcribe_router
from dotenv import load_dotenv
from backend.core.rate_limit import limiter

from backend.auth.router import router as auth_router
from backend.workflow.planner.router import router as planner_router
from backend.workflow.engine.router import router as engine_router
from backend.workflow.crud.router import router as crud_router
from backend.workflow.validator.router import router as validator_router
from backend.scheduler.router import router as scheduler_router
from backend.scheduler.service import scheduler_service
from backend.core.config import get_settings
from backend.core.redis import close_redis, get_redis
from backend.intent_parser.router import router as intent_router
from backend.followup_engine.router import router as followup_router
from backend.gmail.router import router as gmail_router
from backend.integrations.router import router as integrations_router
from backend.database.session import SessionLocal
from sqlalchemy import text

logger = logging.getLogger(__name__)
settings = get_settings()

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )

# Load environment configs from the project root .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))


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

    # 0. Reconcile PostgreSQL enum types (ALTER TYPE ADD VALUE IF NOT EXISTS)
    db_init = SessionLocal()
    try:
        if db_init.bind and db_init.bind.dialect.name == "postgresql":
            for new_val in ("google_drive", "airtable", "twilio"):
                try:
                    # Note: ALTER TYPE ADD VALUE cannot run inside a transaction block in older postgres
                    # but with autocommit or isolation level/check we execute cleanly
                    connection = db_init.connection().execution_options(isolation_level="AUTOCOMMIT")
                    connection.execute(text(f"ALTER TYPE integration_service ADD VALUE IF NOT EXISTS '{new_val}'"))
                except Exception as e_enum:
                    logger.debug(f"[Startup] Enum reconciliation ({new_val}): {e_enum}")
            logger.info("[Startup] PostgreSQL enum types reconciled.")
    except Exception as e:
        logger.warning(f"[Startup] Database enum check check: {e}")
    finally:
        db_init.close()

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
     openapi_url="/api/openapi.json"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

from starlette.exceptions import HTTPException as StarletteHTTPException

def _add_cors_headers(request: Request, headers: dict) -> dict:
    origin = request.headers.get("origin")
    if origin:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    return headers

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    headers = _add_cors_headers(request, dict(exc.headers or {}))
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=headers,
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    headers = _add_cors_headers(request, {})
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal Server Error: {str(exc)}"},
        headers=headers,
    )

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
    allow_origin_regex=r"https://.*\.vercel\.app|http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(intent_router, prefix="/api/v1")
app.include_router(followup_router, prefix="/api/v1")
app.include_router(planner_router, prefix="/api/v1")
app.include_router(engine_router, prefix="/api/v1")
app.include_router(validator_router, prefix="/api/v1")
app.include_router(crud_router, prefix="/api/v1")
app.include_router(scheduler_router, prefix="/api/v1")
app.include_router(gmail_router, prefix="/api/v1")
app.include_router(integrations_router, prefix="/api/v1")
app.include_router(transcribe_router, prefix="/api/v1")


# ─────────────────────────────────────────────────────────────────────────────
# System Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.api_route("/", methods=["GET", "HEAD"], tags=["System"])
async def root():
    return {"name": settings.APP_NAME, "status": "online", "docs": "/docs"}


@app.get("/health", tags=["System"])
async def health_check():
    db_status = False
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_status = True
    except Exception as e:
        logger.warning(f"Health check DB failed: {e}")

    redis_status = False
    try:
        redis = await get_redis()
        await redis.ping()
        redis_status = True
    except Exception as e:
        logger.warning(f"Health check Redis failed: {e}")

    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": "0.1.0",
        "db_connected": db_status,
        "redis_connected": redis_status,
        "scheduler_running": scheduler_service.is_running,
        "has_openai_key": bool(os.getenv("OPENAI_API_KEY")),
        "has_groq_key": bool(os.getenv("GROQ_API_KEY"))
    }


@app.get("/api/v1/scheduler/status", tags=["System"])
def scheduler_status():
    """Quick check if APScheduler is running."""
    return {
        "scheduler_running": scheduler_service.is_running,
    }


# Set up logging format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True)
