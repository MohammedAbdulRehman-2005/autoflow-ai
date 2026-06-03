"""
AutoFlow AI X — Gmail Executor
================================
Handles all Gmail operations: send_email, get_emails, create_draft.

Auth flow: OAuth 2.0 credentials are stored encrypted in the `integrations`
table. At runtime we decrypt, build a google-auth Credentials object,
and initialize the Gmail API client.

Production note: In MVP, credentials_encrypted holds a JSON blob of the
OAuth token. Decrypt with app-level Fernet key before use.
"""

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any
import base64

from backend.workflow.dsl.schema import WorkflowNodeDSL
from backend.workflow.engine.context import ExecutionContext
from backend.workflow.engine.executors.base import BaseExecutor, ExecutorResult

logger = logging.getLogger(__name__)


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
        reply_to: reply-to address
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

        # ── Build MIME message ────────────────────────────────────────────────
        msg = MIMEMultipart("alternative")
        msg["to"] = to if isinstance(to, str) else ", ".join(to)
        msg["subject"] = subject
        if cc:
            msg["cc"] = cc if isinstance(cc, str) else ", ".join(cc)
        if bcc:
            msg["bcc"] = bcc if isinstance(bcc, str) else ", ".join(bcc)

        # Support both plain text and HTML
        if "<html" in body.lower() or "<br" in body.lower():
            msg.attach(MIMEText(body, "html"))
        else:
            msg.attach(MIMEText(body, "plain"))

        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

        # ── Call Gmail API ────────────────────────────────────────────────────
        # In production: decrypt OAuth credentials from integrations table,
        # build google.oauth2.credentials.Credentials, initialize Gmail service.
        #
        # from googleapiclient.discovery import build
        # service = build("gmail", "v1", credentials=credentials)
        # result = service.users().messages().send(
        #     userId="me", body={"raw": raw_message}
        # ).execute()
        # message_id = result.get("id")

        # STUB: log and return success for now (replace with real API call)
        logger.info(f"[Gmail] Sending email to '{to}' | subject='{subject}'")
        message_id = f"stub_msg_{node.id}"

        return ExecutorResult.ok(
            output={
                "message_id": message_id,
                "to": to,
                "subject": subject,
                "status": "sent",
            }
        )


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

        # STUB: return empty list (replace with real API call)
        return ExecutorResult.ok(
            output={
                "emails": [],
                "count": 0,
                "query": query,
            }
        )
