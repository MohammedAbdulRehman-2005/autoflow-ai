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
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("ENCRYPTION_KEY environment variable is not set.")
    return Fernet(key.encode())


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
            "openid",
            "email",
            "profile",
        ],
        "client_id_env": "GOOGLE_CLIENT_ID",
        "client_secret_env": "GOOGLE_CLIENT_SECRET",
        "redirect_uri_env": "GOOGLE_REDIRECT_URI",
        "extra_params": {"access_type": "offline", "prompt": "consent"},
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


def build_oauth_url(provider: str, user_id: uuid.UUID) -> str:
    """Build the OAuth authorization URL for a provider."""
    cfg = PROVIDER_CONFIG.get(provider)
    if not cfg:
        raise ValueError(f"Unknown OAuth provider: {provider}")

    client_id = os.getenv(cfg["client_id_env"], "")
    redirect_uri = os.getenv(cfg["redirect_uri_env"], "")
    scopes = " ".join(cfg["scopes"])
    state = f"{user_id}:{provider}"

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
) -> Integration:
    """
    Exchange an OAuth authorization code for tokens.
    Saves encrypted tokens to the DB and returns the Integration row.
    """
    import httpx

    cfg = PROVIDER_CONFIG[provider]
    client_id = os.getenv(cfg["client_id_env"], "")
    client_secret = os.getenv(cfg["client_secret_env"], "")
    redirect_uri = os.getenv(cfg["redirect_uri_env"], "")

    # Parse state to get user_id
    user_id_str, _ = state.split(":", 1)
    user_id = uuid.UUID(user_id_str)

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

    resp.raise_for_status()
    token_data = resp.json()

    # Build credentials dict to store
    credentials = {
        "access_token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token"),
        "token_type": token_data.get("token_type", "Bearer"),
        "expires_in": token_data.get("expires_in"),
        "scope": token_data.get("scope", ""),
        "raw": token_data,  # keep full response for debugging
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
    row = db.query(Integration).filter(
        Integration.user_id == user_id,
        Integration.service_name == IntegrationService(service),
    ).first()
    if not row:
        return False
    row.is_active = False
    db.commit()
    return True
