"""
AutoFlow AI X — Gmail Executor
================================
Handles all Gmail operations: send_email, get_emails, create_draft.

Auth flow: OAuth 2.0 credentials are stored encrypted in the `integrations`
table. At runtime we decrypt, refresh the access token if expired, and
call the Gmail REST API directly via httpx (no google-auth library required).

Token storage shape (from integrations.service.py):
  {
    "access_token": "ya29...",
    "refresh_token": "1//...",
    "token_type": "Bearer",
    "expires_in": 3599,
    "scope": "...",
    "raw": { ... full token response ... }
  }
"""

import base64
import logging
import os
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import httpx

from backend.workflow.dsl.schema import WorkflowNodeDSL
from backend.workflow.engine.context import ExecutionContext
from backend.workflow.engine.executors.base import BaseExecutor, ExecutorResult

logger = logging.getLogger(__name__)

GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


def _get_google_credentials(context: "ExecutionContext") -> dict | None:
    """
    Retrieve and return Google OAuth credentials for the user.

    Checks context.get_secret("gmail") first (populated by CredentialResolver
    before the node runs). Falls back to a direct DB lookup for call sites
    that don't go through the WorkflowRunner (e.g. tests, legacy paths).

    Returns the decrypted credentials dict, or None if not connected.
    """
    # Fast path: CredentialResolver already populated the secret this run.
    cached = context.get_secret("gmail")
    if cached is not None:
        return cached

    # Fallback: direct DB query (pre-CredentialResolver behaviour).
    try:
        from backend.integrations.service import decrypt_credentials
        from backend.database.models import Integration, IntegrationService

        db = context.db
        user_id = context.user_id

        if db is None or user_id is None:
            logger.warning("[Gmail] No DB session or user_id in context.")
            return None

        integration = (
            db.query(Integration)
            .filter(
                Integration.user_id == user_id,
                Integration.service_name == IntegrationService.gmail,
                Integration.is_active == True,
            )
            .first()
        )

        if not integration:
            logger.warning(f"[Gmail] No active Gmail integration found for user {user_id}.")
            return None

        return decrypt_credentials(integration.credentials_encrypted)

    except Exception as exc:
        logger.error(f"[Gmail] Failed to retrieve credentials: {exc}", exc_info=True)
        return None


async def _get_valid_access_token(creds: dict) -> str | None:
    """
    Return a valid access token, refreshing it if necessary.
    """
    access_token = creds.get("access_token")
    refresh_token = creds.get("refresh_token")

    if not access_token:
        return None

    # Try a cheap token-info check
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(
            f"https://oauth2.googleapis.com/tokeninfo?access_token={access_token}"
        )
        if r.status_code == 200:
            return access_token

    # Token is expired — refresh it
    if not refresh_token:
        logger.warning("[Gmail] Access token expired and no refresh token available.")
        return None

    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")

    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
            },
        )
        if r.status_code != 200:
            logger.warning(f"[Gmail] Token refresh failed: {r.status_code} {r.text}")
            return None

        new_token_data = r.json()
        return new_token_data.get("access_token")


class GmailGetEmailsExecutor(BaseExecutor):
    """
    Fetches emails from Gmail matching a query.

    Required params:
        query   : Gmail search query (e.g. "from:patient@example.com is:unread")

    Optional params:
        max_results : max emails to return (default 10)
    """

    async def execute(
        self,
        node: WorkflowNodeDSL,
        context: ExecutionContext,
        resolved_params: dict[str, Any],
    ) -> ExecutorResult:
        query = resolved_params.get("query", "is:unread")
        max_results = int(resolved_params.get("max_results", 10))

        logger.info(f"[Gmail] Fetching emails | query='{query}' max={max_results}")

        creds = _get_google_credentials(context)
        if not creds:
            return ExecutorResult.fail(
                "Gmail is not connected. Please connect Gmail in Settings → Integrations."
            )

        token = await _get_valid_access_token(creds)
        if not token:
            return ExecutorResult.fail(
                "Gmail access token is expired or invalid. Please reconnect Gmail in Settings."
            )

        headers = {"Authorization": f"Bearer {token}"}

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                # Step 1: list matching message IDs
                list_resp = await client.get(
                    f"{GMAIL_API_BASE}/messages",
                    headers=headers,
                    params={"q": query, "maxResults": max_results},
                )
                list_resp.raise_for_status()
                list_data = list_resp.json()

            messages_meta = list_data.get("messages", [])
            if not messages_meta:
                logger.info("[Gmail] No matching emails found.")
                return ExecutorResult.ok(output={"emails": [], "count": 0, "query": query})

            # Step 2: fetch each message's details
            emails = []
            async with httpx.AsyncClient(timeout=20.0) as client:
                for msg_meta in messages_meta[:max_results]:
                    msg_resp = await client.get(
                        f"{GMAIL_API_BASE}/messages/{msg_meta['id']}",
                        headers=headers,
                        params={"format": "metadata", "metadataHeaders": ["Subject", "From", "Date", "To"]},
                    )
                    if msg_resp.status_code != 200:
                        continue

                    msg = msg_resp.json()
                    headers_list = msg.get("payload", {}).get("headers", [])
                    header_map = {h["name"].lower(): h["value"] for h in headers_list}

                    emails.append({
                        "id": msg["id"],
                        "thread_id": msg.get("threadId"),
                        "subject": header_map.get("subject", "(No Subject)"),
                        "from": header_map.get("from", ""),
                        "to": header_map.get("to", ""),
                        "date": header_map.get("date", ""),
                        "snippet": msg.get("snippet", ""),
                        "labels": msg.get("labelIds", []),
                    })

            logger.info(f"[Gmail] Fetched {len(emails)} email(s).")
            return ExecutorResult.ok(
                output={
                    "emails": emails,
                    "count": len(emails),
                    "query": query,
                }
            )

        except httpx.HTTPStatusError as exc:
            return ExecutorResult.fail(
                f"Gmail API HTTP error: {exc.response.status_code} — {exc.response.text}"
            )
        except Exception as exc:
            return ExecutorResult.fail(f"Gmail fetch error: {exc}")


class GmailSendEmailExecutor(BaseExecutor):
    """
    Sends an email via Gmail API.

    Required params:
        to      : recipient email (string or comma-separated)
        subject : email subject
        body    : plain-text or HTML body

    Optional params:
        cc      : CC recipients
        bcc     : BCC recipients
    """

    async def execute(
        self,
        node: WorkflowNodeDSL,
        context: ExecutionContext,
        resolved_params: dict[str, Any],
    ) -> ExecutorResult:
        to = resolved_params.get("to", "")
        subject = resolved_params.get("subject", "(No Subject)")
        body = resolved_params.get("body", "")
        cc = resolved_params.get("cc", "")
        bcc = resolved_params.get("bcc", "")

        if not to:
            return ExecutorResult.fail("'to' is required for send_email but was empty.")

        creds = _get_google_credentials(context)
        if not creds:
            return ExecutorResult.fail(
                "Gmail is not connected. Please connect Gmail in Settings → Integrations."
            )

        token = await _get_valid_access_token(creds)
        if not token:
            return ExecutorResult.fail(
                "Gmail access token is expired or invalid. Please reconnect Gmail in Settings."
            )

        # Build MIME message
        msg = MIMEMultipart("alternative")
        msg["to"] = to if isinstance(to, str) else ", ".join(to)
        msg["subject"] = subject
        if cc:
            msg["cc"] = cc if isinstance(cc, str) else ", ".join(cc)
        if bcc:
            msg["bcc"] = bcc if isinstance(bcc, str) else ", ".join(bcc)

        if "<html" in body.lower() or "<br" in body.lower():
            msg.attach(MIMEText(body, "html"))
        else:
            msg.attach(MIMEText(body, "plain"))

        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{GMAIL_API_BASE}/messages/send",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json={"raw": raw_message},
                )
                resp.raise_for_status()
                data = resp.json()

            logger.info(f"[Gmail] Email sent to '{to}' | message_id={data.get('id')}")
            return ExecutorResult.ok(
                output={
                    "message_id": data.get("id"),
                    "to": to,
                    "subject": subject,
                    "status": "sent",
                }
            )
        except httpx.HTTPStatusError as exc:
            return ExecutorResult.fail(
                f"Gmail send error: {exc.response.status_code} — {exc.response.text}"
            )
        except Exception as exc:
            return ExecutorResult.fail(f"Gmail send error: {exc}")
