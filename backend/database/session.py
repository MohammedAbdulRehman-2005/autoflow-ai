"""
Database session factory and engine configuration.

Usage:
    from backend.database.session import get_db

    # In a FastAPI endpoint:
    async def my_endpoint(db: Session = Depends(get_db)):
        ...
"""

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def normalize_database_url(url: str) -> str:
    """
    Normalizes the database connection URL for SQLAlchemy:
      - Converts legacy 'postgres://' schema to 'postgresql://'
      - Intelligently detects installed postgres driver (psycopg vs psycopg2)
        and updates the driver prefix to prevent ModuleNotFoundError.
    """
    if not url:
        return url

    # Heroku / Supabase legacy prefix compatibility
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    # Route postgresql dialect according to installed driver
    if url.startswith("postgresql+psycopg://"):
        try:
            import psycopg  # noqa: F401
        except ImportError:
            try:
                import psycopg2  # noqa: F401
                url = url.replace("postgresql+psycopg://", "postgresql+psycopg2://", 1)
                logger.info("[DB] 'psycopg' v3 not found, fell back to 'psycopg2' driver.")
            except ImportError:
                pass
    elif url.startswith("postgresql+psycopg2://"):
        try:
            import psycopg2  # noqa: F401
        except ImportError:
            try:
                import psycopg  # noqa: F401
                url = url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
                logger.info("[DB] 'psycopg2' not found, fell back to 'psycopg' v3 driver.")
            except ImportError:
                pass
    elif url.startswith("postgresql://"):
        try:
            import psycopg  # noqa: F401
        except ImportError:
            try:
                import psycopg2  # noqa: F401
                url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
                logger.info("[DB] Default 'psycopg' not found, routing 'postgresql://' to 'psycopg2'.")
            except ImportError:
                pass

    return url


DATABASE_URL = normalize_database_url(settings.DATABASE_URL)

engine_kwargs = {
    "pool_pre_ping": True,   # Detects dropped connections before using them
    "echo": False,            # Set True to log all SQL queries (dev only)
}

# Only configure connection pool sizing on network database dialects (e.g. PostgreSQL)
if not DATABASE_URL.startswith("sqlite"):
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency that yields a database session and ensures cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
