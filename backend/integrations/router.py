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
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.database.models import User
from backend.database.session import get_db
from backend.integrations.service import (
    build_oauth_url,
    disconnect_integration,
    exchange_code_for_tokens,
    list_user_integrations,
    save_apikey_integration,
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


# ---------------------------------------------------------------------------
# Start OAuth flow
# ---------------------------------------------------------------------------

@router.get("/{provider}/connect")
def connect_integration(
    provider: str,
    current_user: User = Depends(get_current_user),
):
    """
    Redirect the user to the OAuth provider's consent screen.
    Supported providers: google, slack, notion, hubspot, salesforce
    """
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
                   f"Add {PROVIDER_CONFIG[provider]['client_id_env']} to Railway environment variables.",
        )

    url = build_oauth_url(provider, current_user.id)
    return RedirectResponse(url=url)


# ---------------------------------------------------------------------------
# OAuth Callback
# ---------------------------------------------------------------------------

@router.get("/callback/{provider}")
async def oauth_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    Google / Slack / Notion / HubSpot / Salesforce redirect back here with ?code=...&state=...
    We exchange the code for tokens, save them encrypted, then redirect to the frontend.
    """
    try:
        integration = await exchange_code_for_tokens(
            provider=provider,
            code=code,
            state=state,
            db=db,
        )
        # Redirect to frontend settings page with success message
        redirect_url = (
            f"{FRONTEND_URL}/settings?integration={provider}&status=connected"
        )
        return RedirectResponse(url=redirect_url)
    except Exception as e:
        redirect_url = (
            f"{FRONTEND_URL}/settings?integration={provider}&status=error&msg={str(e)[:200]}"
        )
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
