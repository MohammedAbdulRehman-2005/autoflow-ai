"""
AutoFlow AI — Integration Context Fetcher
==========================================
Fetches live context (e.g. Slack channels) from user integrations 
to inject into the AI Planner prompt. Uses a short-lived in-memory cache.
"""

import logging
import time
import uuid
import httpx
from sqlalchemy.orm import Session
from backend.database.models import Integration, IntegrationService
from backend.integrations.service import decrypt_credentials

logger = logging.getLogger(__name__)

# Simple in-memory cache: { "user_id_str": {"data": str, "expires_at": float} }
_SLACK_CHANNELS_CACHE: dict[str, dict] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes


async def fetch_slack_channels_context(user_id: uuid.UUID, db: Session) -> str | None:
    """
    Fetches the list of Slack channels the user's bot is a member of.
    Returns a formatted string for the LLM prompt, or None if failed/unconnected.
    """
    user_id_str = str(user_id)
    
    # Check cache
    cached = _SLACK_CHANNELS_CACHE.get(user_id_str)
    if cached and time.time() < cached["expires_at"]:
        return cached["data"]

    # Retrieve integration
    integration = (
        db.query(Integration)
        .filter(
            Integration.user_id == user_id,
            Integration.service_name == IntegrationService.slack,
            Integration.is_active == True,
        )
        .first()
    )
    if not integration or not integration.encrypted_credentials:
        return None

    try:
        creds = decrypt_credentials(integration.encrypted_credentials)
        # OAuth v2 bot tokens are usually under access_token
        token = creds.get("access_token") or creds.get("authed_user", {}).get("access_token")
        if not token:
            return None

        # Call Slack conversations.list
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://slack.com/api/conversations.list",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "types": "public_channel,private_channel",
                    "exclude_archived": "true",
                    "limit": "100"
                }
            )
            resp.raise_for_status()
            data = resp.json()

            if not data.get("ok"):
                error_msg = data.get("error", "unknown")
                # Do not log token!
                logger.warning(f"[ContextFetcher] Slack API error: {error_msg}")
                return None

            channels = data.get("channels", [])
            
            # CRITICAL: Only include channels where the bot is a member.
            member_channels = [c for c in channels if c.get("is_member")]

            if not member_channels:
                result_str = "Slack Channels: (No channels found that the bot is invited to. User must invite the bot to a channel first.)"
            else:
                formatted_list = ", ".join(f"#{c.get('name')} (ID: {c.get('id')})" for c in member_channels)
                result_str = f"Slack Channels: {formatted_list}"

            # Save to cache
            _SLACK_CHANNELS_CACHE[user_id_str] = {
                "data": result_str,
                "expires_at": time.time() + CACHE_TTL_SECONDS
            }
            return result_str

    except Exception as e:
        logger.warning(f"[ContextFetcher] Failed to fetch Slack context: {str(e)}")
        return None
