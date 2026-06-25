"""
AutoFlow AI X — Slack Executor
================================
Handles Slack operations: post_message.

Auth flow:
  - The user connects Slack via OAuth (integrations layer).
  - The Slack response stores `authed_user.access_token` (user token) OR
    `access_token` (bot token) in the encrypted credentials blob.
  - At runtime we decrypt the blob, pull out `access_token` (the bot token),
    and call the Slack Web API with it.

Slack Web API reference:
  https://api.slack.com/methods/chat.postMessage
"""

import logging
import os
from typing import Any

import httpx

from backend.workflow.dsl.schema import WorkflowNodeDSL
from backend.workflow.engine.context import ExecutionContext
from backend.workflow.engine.executors.base import BaseExecutor, ExecutorResult

logger = logging.getLogger(__name__)

SLACK_POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"


def _get_slack_token(context: ExecutionContext) -> str | None:
    """
    Retrieve the Slack bot token from the user's stored integration credentials.

    The token is stored in the encrypted credentials blob under the key
    'access_token' (bot token from Slack OAuth v2 response) OR
    'authed_user.access_token' (user token, less common for bots).

    Returns None if no Slack integration is found or the token is missing.
    """
    try:
        from backend.integrations.service import decrypt_credentials
        from backend.database.models import Integration, IntegrationService

        db = context.db
        user_id = context.user_id

        if db is None or user_id is None:
            logger.warning("[Slack] No DB session or user_id in context — cannot retrieve token.")
            return None

        integration = (
            db.query(Integration)
            .filter(
                Integration.user_id == user_id,
                Integration.service_name == IntegrationService.slack,
                Integration.is_active == True,
            )
            .first()
        )

        if not integration:
            logger.warning(f"[Slack] No active Slack integration found for user {user_id}.")
            return None

        creds = decrypt_credentials(integration.credentials_encrypted)

        # Slack OAuth v2 bot token lives at the top-level 'access_token'
        token = creds.get("access_token")
        if not token:
            # Fallback: user token (authed_user.access_token)
            raw = creds.get("raw", {})
            token = raw.get("authed_user", {}).get("access_token")

        return token

    except Exception as exc:
        logger.error(f"[Slack] Failed to retrieve token: {exc}", exc_info=True)
        return None


class SlackPostMessageExecutor(BaseExecutor):
    """
    Posts a message to a Slack channel.

    Required params:
        channel : Slack channel name ('#all-autoflow-ai') or channel ID ('C08XXXXXXX')
        text    : Message text (supports Slack mrkdwn formatting)

    Optional params:
        blocks      : Slack Block Kit JSON array for rich formatting
        username    : Override the bot display name
        icon_emoji  : Override the bot icon (e.g. ':robot_face:')
    """

    async def execute(
        self,
        node: WorkflowNodeDSL,
        context: ExecutionContext,
        resolved_params: dict[str, Any],
    ) -> ExecutorResult:
        channel = os.getenv("SLACK_CHANNEL") or resolved_params.get("channel", "")
        text = resolved_params.get("text", "")
        blocks = resolved_params.get("blocks")
        username = resolved_params.get("username")
        icon_emoji = resolved_params.get("icon_emoji")

        if not channel:
            return ExecutorResult.fail("'channel' is required for slack.post_message but was empty.")
        if not text and not blocks:
            return ExecutorResult.fail("'text' or 'blocks' is required for slack.post_message.")

        # ── Retrieve bot token ────────────────────────────────────────────────
        token = _get_slack_token(context)
        if not token:
            return ExecutorResult.fail(
                "Slack integration is not connected or token is missing. "
                "Please reconnect Slack in Settings."
            )

        # ── Build request payload ─────────────────────────────────────────────
        payload: dict[str, Any] = {
            "channel": channel,
            "text": text,
        }
        if blocks:
            payload["blocks"] = blocks
        if username:
            payload["username"] = username
        if icon_emoji:
            payload["icon_emoji"] = icon_emoji

        logger.info(f"[Slack] Posting message to '{channel}'")

        # ── Call Slack Web API ────────────────────────────────────────────────
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    SLACK_POST_MESSAGE_URL,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json; charset=utf-8",
                    },
                    json=payload,
                )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            return ExecutorResult.fail(
                f"Slack API HTTP error: {exc.response.status_code} — {exc.response.text}"
            )
        except Exception as exc:
            return ExecutorResult.fail(f"Slack API request failed: {exc}")

        # ── Slack returns 200 even on errors — check 'ok' field ───────────────
        if not data.get("ok"):
            error_code = data.get("error", "unknown_error")
            return ExecutorResult.fail(
                f"Slack API returned an error: {error_code}. "
                f"Common causes: invalid channel name, bot not invited to channel, "
                f"missing 'chat:write' scope."
            )

        logger.info(
            f"[Slack] Message posted to '{channel}' | ts={data.get('ts')} "
            f"| channel_id={data.get('channel')}"
        )

        return ExecutorResult.ok(
            output={
                "ok": True,
                "channel": data.get("channel"),
                "ts": data.get("ts"),
                "message": data.get("message", {}).get("text", text),
            }
        )
