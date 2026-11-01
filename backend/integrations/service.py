"""
AutoFlow AI — Integration Encryption & Token Service
=====================================================
Handles:
  - Fernet AES encryption/decryption of OAuth tokens
  - Building OAuth redirect URLs per provider
  - Exchanging auth codes for tokens
  - Listing / disconnecting integrations
"""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from backend.database.models import Integration, IntegrationService

# ---------------------------------------------------------------------------
# Encryption helpers
# ---------------------------------------------------------------------------

def _get_fernet() -> Fernet:
    try:
        from backend.core.config import get_settings
        settings = get_settings()
        key = settings.FERNET_KEY or settings.ENCRYPTION_KEY or os.getenv("FERNET_KEY") or os.getenv("ENCRYPTION_KEY")
    except Exception:
        key = os.getenv("FERNET_KEY") or os.getenv("ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("Neither FERNET_KEY nor ENCRYPTION_KEY environment variable is configured.")
    return Fernet(key.encode() if isinstance(key, str) else key)



def encrypt_credentials(data: dict) -> str:
    """Serialize a dict to JSON and encrypt it with Fernet."""
    raw = json.dumps(data).encode()
    return _get_fernet().encrypt(raw).decode()


def decrypt_credentials(encrypted: str) -> dict:
    """Decrypt a Fernet-encrypted string and return the dict."""
    raw = _get_fernet().decrypt(encrypted.encode())
    return json.loads(raw)


# ---------------------------------------------------------------------------
# OAuth URL builders (one per provider)
# ---------------------------------------------------------------------------

PROVIDER_CONFIG: dict[str, dict] = {
    "google": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": [
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/calendar.events",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive",
            "openid",
            "email",
            "profile",
        ],
        "client_id_env": "GOOGLE_CLIENT_ID",
        "client_secret_env": "GOOGLE_CLIENT_SECRET",
        "redirect_uri_env": "GOOGLE_REDIRECT_URI",
        "extra_params": {"access_type": "offline", "prompt": "select_account consent"},
    },
    "slack": {
        "auth_url": "https://slack.com/oauth/v2/authorize",
        "token_url": "https://slack.com/api/oauth.v2.access",
        "scopes": ["chat:write", "channels:read", "channels:history", "users:read"],
        "client_id_env": "SLACK_CLIENT_ID",
        "client_secret_env": "SLACK_CLIENT_SECRET",
        "redirect_uri_env": "SLACK_REDIRECT_URI",
        "extra_params": {},
    },
    "notion": {
        "auth_url": "https://api.notion.com/v1/oauth/authorize",
        "token_url": "https://api.notion.com/v1/oauth/token",
        "scopes": [],  # Notion uses owner-based auth, no explicit scopes
        "client_id_env": "NOTION_CLIENT_ID",
        "client_secret_env": "NOTION_CLIENT_SECRET",
        "redirect_uri_env": "NOTION_REDIRECT_URI",
        "extra_params": {"owner": "user"},
    },
    "hubspot": {
        "auth_url": "https://app.hubspot.com/oauth/authorize",
        "token_url": "https://api.hubapi.com/oauth/v1/token",
        "scopes": [
            "contacts",
            "crm.objects.contacts.read",
            "crm.objects.contacts.write",
            "crm.objects.deals.read",
        ],
        "client_id_env": "HUBSPOT_CLIENT_ID",
        "client_secret_env": "HUBSPOT_CLIENT_SECRET",
        "redirect_uri_env": "HUBSPOT_REDIRECT_URI",
        "extra_params": {},
    },
    "salesforce": {
        "auth_url": "https://login.salesforce.com/services/oauth2/authorize",
        "token_url": "https://login.salesforce.com/services/oauth2/token",
        "scopes": ["api", "refresh_token"],
        "client_id_env": "SALESFORCE_CLIENT_ID",
        "client_secret_env": "SALESFORCE_CLIENT_SECRET",
        "redirect_uri_env": "SALESFORCE_REDIRECT_URI",
        "extra_params": {},
    },
}

# Stripe is API-key based (no OAuth flow)
APIKEY_PROVIDERS = {"stripe"}


def get_provider_redirect_uri(provider: str) -> str:
    cfg = PROVIDER_CONFIG.get(provider, {})
    env_var = cfg.get("redirect_uri_env", "")
    val = os.getenv(env_var, "").strip() if env_var else ""
    if not val or "railway.app" in val:
        return f"https://autoflow-ai-1.onrender.com/api/v1/integrations/callback/{provider}"
    return val


import json
import logging
import secrets
import time
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

OAUTH_STATE_TTL_SECONDS = 600  # 10 minutes
_OAUTH_STATE_KEY_PREFIX = "oauth:state:"

class OAuthStateStoreUnavailableError(RuntimeError):
    """Raised when the backing Redis store for OAuth state cannot be reached."""
    pass

_LUA_ATOMIC_GETDEL = """
local val = redis.call('GET', KEYS[1])
if val then
    redis.call('DEL', KEYS[1])
end
return val
"""


async def generate_oauth_state(user_id: uuid.UUID, provider: str, redis: aioredis.Redis) -> str:
    """Generate a single-use, cryptographically secure 256-bit OAuth state token bound to user and provider,
    stored durably in Redis with 10-minute TTL."""
    state_token = secrets.token_urlsafe(32)
    key = f"{_OAUTH_STATE_KEY_PREFIX}{state_token}"
    payload = json.dumps({
        "user_id": str(user_id),
        "provider": provider,
        "created_at": time.time(),
    })
    try:
        await redis.setex(key, OAUTH_STATE_TTL_SECONDS, payload)
    except Exception as e:
        logger.error(f"Failed to store OAuth state in Redis for provider '{provider}': {e}")
        raise OAuthStateStoreUnavailableError(
            "OAuth state storage service is currently unavailable. Please try again later."
        ) from e
    return state_token


async def verify_and_consume_oauth_state(state_token: str, provider: str, redis: aioredis.Redis) -> uuid.UUID:
    """Atomically validate and consume the single-use OAuth state token from Redis.
    Prevents replay, multi-instance races, and CSRF attacks."""
    if not state_token:
        raise ValueError("Missing OAuth state token.")

    key = f"{_OAUTH_STATE_KEY_PREFIX}{state_token}"
    try:
        raw_val = await redis.eval(_LUA_ATOMIC_GETDEL, 1, key)
    except Exception as e:
        logger.error(f"Failed to consume OAuth state from Redis: {e}")
        raise OAuthStateStoreUnavailableError(
            "OAuth state storage service is currently unavailable to verify the authentication request."
        ) from e

    if not raw_val:
        raise ValueError("Invalid, expired, or previously consumed OAuth state token.")

    if isinstance(raw_val, bytes):
        raw_val = raw_val.decode("utf-8")

    try:
        state_data = json.loads(raw_val)
    except (json.JSONDecodeError, TypeError) as e:
        raise ValueError(f"Corrupted OAuth state payload: {e}")

    if state_data.get("provider") != provider:
        raise ValueError(f"OAuth state was created for provider '{state_data.get('provider')}', not '{provider}'.")

    user_id_str = state_data.get("user_id")
    if not user_id_str:
        raise ValueError("Invalid OAuth state: missing user_id.")

    return uuid.UUID(user_id_str)


async def build_oauth_url(provider: str, user_id: uuid.UUID, redis: aioredis.Redis) -> str:
    """Build the OAuth authorization URL for a provider with an unpredictable state parameter."""
    cfg = PROVIDER_CONFIG.get(provider)
    if not cfg:
        raise ValueError(f"Unknown OAuth provider: {provider}")

    client_id = os.getenv(cfg["client_id_env"], "")
    redirect_uri = get_provider_redirect_uri(provider)
    scope_separator = "," if provider == "slack" else " "
    scopes = scope_separator.join(cfg["scopes"])
    state = await generate_oauth_state(user_id, provider, redis)

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scopes,
        "state": state,
        **cfg.get("extra_params", {}),
    }

    from urllib.parse import urlencode
    return f"{cfg['auth_url']}?{urlencode(params)}"


async def exchange_code_for_tokens(
    provider: str,
    code: str,
    state: str,
    db: Session,
    redis: aioredis.Redis,
) -> Integration:
    """
    Exchange an OAuth authorization code for tokens.
    Saves encrypted tokens to the DB and returns the Integration row.
    """
    import httpx

    cfg = PROVIDER_CONFIG[provider]
    client_id = os.getenv(cfg["client_id_env"], "")
    client_secret = os.getenv(cfg["client_secret_env"], "")
    redirect_uri = get_provider_redirect_uri(provider)

    # Validate and consume single-use state token to get user_id
    user_id = await verify_and_consume_oauth_state(state, provider, redis)

    # Exchange code → tokens
    token_params = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
    }

    # Notion uses Basic auth for token exchange
    auth = None
    if provider == "notion":
        import base64
        creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        headers = {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}
        async with httpx.AsyncClient() as client:
            resp = await client.post(cfg["token_url"], json={"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri}, headers=headers)
    else:
        async with httpx.AsyncClient() as client:
            resp = await client.post(cfg["token_url"], data=token_params)

    if resp.is_error:
        logger.error(f"OAuth token exchange failed for provider '{provider}': HTTP {resp.status_code}")
        raise ValueError(f"OAuth token exchange failed with provider (HTTP {resp.status_code}).")
    token_data = resp.json()

    # Build credentials dict to store (raw response omitted for security - P0 #7)
    credentials = {
        "access_token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token"),
        "token_type": token_data.get("token_type", "Bearer"),
        "expires_in": token_data.get("expires_in"),
        "scope": token_data.get("scope", ""),
    }

    # Determine service_name (google covers gmail/sheets/calendar)
    if provider == "google":
        service_name = IntegrationService.gmail  # primary; we store once for all Google services
    else:
        service_name = IntegrationService(provider)

    encrypted = encrypt_credentials(credentials)

    # Upsert: update if exists, create if not
    existing = (
        db.query(Integration)
        .filter(
            Integration.user_id == user_id,
            Integration.service_name == service_name,
        )
        .first()
    )
    if existing:
        existing.credentials_encrypted = encrypted
        existing.is_active = True
        existing.last_synced_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return existing
    else:
        integration = Integration(
            user_id=user_id,
            service_name=service_name,
            display_name=f"{provider.capitalize()} Account",
            credentials_encrypted=encrypted,
            is_active=True,
            last_synced_at=datetime.now(timezone.utc),
        )
        db.add(integration)
        db.commit()
        db.refresh(integration)
        return integration


def save_apikey_integration(
    user_id: uuid.UUID,
    service: str,
    credentials: dict,
    db: Session,
) -> Integration:
    """Save API-key-based integrations (e.g. Stripe)."""
    service_name = IntegrationService(service)
    encrypted = encrypt_credentials(credentials)

    existing = (
        db.query(Integration)
        .filter(Integration.user_id == user_id, Integration.service_name == service_name)
        .first()
    )
    if existing:
        existing.credentials_encrypted = encrypted
        existing.is_active = True
        existing.last_synced_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return existing

    integration = Integration(
        user_id=user_id,
        service_name=service_name,
        display_name=f"{service.capitalize()} Account",
        credentials_encrypted=encrypted,
        is_active=True,
        last_synced_at=datetime.now(timezone.utc),
    )
    db.add(integration)
    db.commit()
    db.refresh(integration)
    return integration


def list_user_integrations(user_id: uuid.UUID, db: Session) -> list[dict]:
    """Return all connected integrations for a user (without exposing tokens)."""
    rows = db.query(Integration).filter(
        Integration.user_id == user_id,
        Integration.is_active == True,
    ).all()
    return [
        {
            "id": str(r.id),
            "service": r.service_name.value,
            "display_name": r.display_name,
            "connected": True,
            "last_synced_at": r.last_synced_at.isoformat() if r.last_synced_at else None,
        }
        for r in rows
    ]


def disconnect_integration(user_id: uuid.UUID, service: str, db: Session) -> bool:
    """Mark an integration as inactive (soft delete)."""
    google_suite = {"google", "gmail", "google_sheets", "google_calendar", "google_drive"}
    if service in google_suite:
        rows = db.query(Integration).filter(
            Integration.user_id == user_id,
            Integration.service_name.in_([
                IntegrationService.gmail,
                IntegrationService.google_sheets,
                IntegrationService.google_calendar,
            ]),
        ).all()
        if not rows:
            return False
        for row in rows:
            row.is_active = False
        db.commit()
        return True

    row = db.query(Integration).filter(
        Integration.user_id == user_id,
        Integration.service_name == IntegrationService(service),
    ).first()
    if not row:
        return False
    row.is_active = False
    db.commit()
    return True
