"""
Database session factory and engine configuration.

Usage:
    from backend.database.session import get_db

    # In a FastAPI endpoint:
    async def my_endpoint(db: Session = Depends(get_db)):
        ...
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.core.config import get_settings

settings=get_settings()

DATABASE_URL = settings.DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # Detects dropped connections before using them
    pool_size=10,          # Max connections in pool
    max_overflow=20,       # Max connections beyond pool_size
    echo=False,            # Set True to log all SQL queries (dev only)
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency that yields a database session and ensures cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
