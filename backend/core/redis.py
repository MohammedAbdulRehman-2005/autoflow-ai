"""
AutoFlow AI X — Redis client singleton.
Used for refresh token storage and future caching/queuing needs.
"""

import redis.asyncio as aioredis
from backend.core.config import get_settings

settings = get_settings()

# Module-level pool — created once, reused across all requests
_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """
    FastAPI dependency: yields a shared async Redis client.
    The connection pool is shared across all requests.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis() -> None:
    """Close the Redis connection pool on app shutdown."""
    global _redis_client
    if _redis_client:
        try:
            await _redis_client.aclose()
        except Exception:
            pass
        _redis_client = None
