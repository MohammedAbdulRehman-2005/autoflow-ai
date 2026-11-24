"""
AutoFlow AI — Integrations Router
===================================
Endpoints:
  GET  /api/v1/integrations/                          — list connected integrations
  GET  /api/v1/integrations/{provider}/connect        — start OAuth flow
  GET  /api/v1/integrations/callback/{provider}       — OAuth callback
  POST /api/v1/integrations/stripe/connect            — connect Stripe via API key
  DELETE /api/v1/integrations/{service}               — disconnect an integration
"""

import os
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

import redis.asyncio as aioredis

from backend.auth.dependencies import get_current_user
from backend.core.redis import get_redis
from backend.database.models import User
from backend.database.session import get_db
from backend.integrations.service import (
    build_oauth_url,
    disconnect_integration,
    exchange_code_for_tokens,
    list_user_integrations,
    save_apikey_integration,
    OAuthStateStoreUnavailableError,
    PROVIDER_CONFIG,
    APIKEY_PROVIDERS,
)

router = APIRouter(prefix="/integrations", tags=["Integrations"])

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://autoflow-ai-ebon.vercel.app")

# ---------------------------------------------------------------------------
# List connected integrations
# ---------------------------------------------------------------------------

@router.get("/")
def get_integrations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all connected integrations for the current user."""
    return list_user_integrations(current_user.id, db)


def verify_no_query_token(request: Request):
    """Strictly disallow passing authentication tokens in query strings."""
    if "token" in request.query_params:
        raise HTTPException(
            status_code=400,
            detail="Passing authentication tokens in query strings is prohibited. "
                   "Provide your Bearer token in the Authorization header.",
        )


@router.api_route(
    "/{provider}/connect",
    methods=["GET", "POST"],
    dependencies=[Depends(verify_no_query_token)],
)
async def connect_integration(
    provider: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    redis: aioredis.Redis = Depends(get_redis),
    db: Session = Depends(get_db),
):
    """
    Start the OAuth flow for a provider.
    Authentication MUST be provided via Authorization: Bearer header.
    Query-string tokens are strictly rejected.
    Returns the authorization URL for client redirection.
    """
    # Strict rejection of query-token authentication
    if "token" in request.query_params:
        raise HTTPException(
            status_code=400,
            detail="Passing authentication tokens in query strings is prohibited. "
                   "Provide your Bearer token in the Authorization header.",
        )

    if provider in APIKEY_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"{provider} uses API keys, not OAuth. Use POST /{provider}/connect instead.",
        )
    if provider not in PROVIDER_CONFIG:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")

    client_id = os.getenv(PROVIDER_CONFIG[provider]["client_id_env"])
    if not client_id:
        raise HTTPException(
            status_code=503,
            detail=f"{provider.capitalize()} OAuth is not configured on this server yet. "
                   f"Add {PROVIDER_CONFIG[provider]['client_id_env']} to environment variables.",
        )

    url = await build_oauth_url(provider, current_user.id, redis)

    # If invoked directly via browser navigation with text/html Accept header, redirect.
    # Otherwise, return JSON response with URL for SPA navigation.
    accept = request.headers.get("accept", "")
    if "text/html" in accept and "application/json" not in accept:
        return RedirectResponse(url=url)

    return {"url": url}


# ---------------------------------------------------------------------------
# OAuth Callback
# ---------------------------------------------------------------------------

@router.get("/callback/{provider}")
async def oauth_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(...),
    redis: aioredis.Redis = Depends(get_redis),
    db: Session = Depends(get_db),
):
    """
    OAuth provider redirects back here with ?code=...&state=...
    Exchanges code for tokens using single-use Redis-backed state validation.
    """
    from urllib.parse import quote
    import logging

    try:
        integration = await exchange_code_for_tokens(
            provider=provider,
            code=code,
            state=state,
            db=db,
            redis=redis,
        )
        redirect_url = f"{FRONTEND_URL}/settings?integration={provider}&status=connected"
        return RedirectResponse(url=redirect_url)
    except Exception as e:
        logging.getLogger(__name__).error(f"[OAuth Callback Error] Provider: {provider}, Error: {e}", exc_info=True)
        # Redact raw error details from client redirect query string (P0 #7)
        if isinstance(e, ValueError):
            err_msg = quote("Invalid, expired, or previously consumed authentication request.")
        elif isinstance(e, OAuthStateStoreUnavailableError):
            err_msg = quote("Authentication state verification service temporarily unavailable.")
        else:
            err_msg = quote("Authentication failed with OAuth provider.")

        redirect_url = f"{FRONTEND_URL}/settings?integration={provider}&status=error&msg={err_msg}"
        return RedirectResponse(url=redirect_url)


# ---------------------------------------------------------------------------
# Stripe API key connect (POST, not OAuth)
# ---------------------------------------------------------------------------

class StripeConnectRequest(BaseModel):
    secret_key: str
    webhook_secret: str | None = None


@router.post("/stripe/connect")
def connect_stripe(
    body: StripeConnectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Connect Stripe using the secret API key (not OAuth)."""
    credentials = {
        "secret_key": body.secret_key,
        "webhook_secret": body.webhook_secret or "",
    }
    integration = save_apikey_integration(
        user_id=current_user.id,
        service="stripe",
        credentials=credentials,
        db=db,
    )
    return {"status": "connected", "integration_id": str(integration.id)}


# ---------------------------------------------------------------------------
# Disconnect
# ---------------------------------------------------------------------------

@router.delete("/{service}")
def delete_integration(
    service: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Disconnect (soft-delete) an integration."""
    ok = disconnect_integration(current_user.id, service, db)
    if not ok:
        raise HTTPException(status_code=404, detail="Integration not found.")
    return {"status": "disconnected", "service": service}
