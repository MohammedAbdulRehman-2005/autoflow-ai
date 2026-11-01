import os
import pytest

# Ensure safe dummy environment variables for tests before importing the application
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-for-testing-only-at-least-32-chars")
os.environ.setdefault("FERNET_KEY", "test-fernet-key-alias-for-test-32bytes=")
os.environ.setdefault("GROQ_API_KEY", "test-groq-api-key")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-api-key")

from fastapi.testclient import TestClient
from backend.main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
