"""
AutoFlow AI X — Notion Executor
=================================
Handles Notion operations: append_row (appends a row to a Notion database).

Auth flow:
  - The user connects Notion via OAuth (integrations layer).
  - The access_token is stored encrypted in the integrations table.
  - Notion OAuth returns a bot-level access_token — we use that directly.

Notion API reference:
  https://developers.notion.com/reference/post-page
  https://developers.notion.com/reference/property-value-object
"""

import logging
from typing import Any

import httpx

from backend.workflow.dsl.schema import WorkflowNodeDSL
from backend.workflow.engine.context import ExecutionContext
from backend.workflow.engine.executors.base import BaseExecutor, ExecutorResult

logger = logging.getLogger(__name__)

NOTION_API_VERSION = "2022-06-28"
NOTION_PAGES_URL = "https://api.notion.com/v1/pages"


def _get_notion_token(context: ExecutionContext) -> str | None:
    """Retrieve the Notion integration token from the user's stored credentials."""
    try:
        from backend.integrations.service import decrypt_credentials
        from backend.database.models import Integration, IntegrationService

        db = context.db
        user_id = context.user_id

        if db is None or user_id is None:
            logger.warning("[Notion] No DB session or user_id in context.")
            return None

        integration = (
            db.query(Integration)
            .filter(
                Integration.user_id == user_id,
                Integration.service_name == IntegrationService.notion,
                Integration.is_active == True,
            )
            .first()
        )

        if not integration:
            logger.warning(f"[Notion] No active Notion integration found for user {user_id}.")
            return None

        creds = decrypt_credentials(integration.credentials_encrypted)
        return creds.get("access_token")

    except Exception as exc:
        logger.error(f"[Notion] Failed to retrieve token: {exc}", exc_info=True)
        return None


def _build_notion_properties(row: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a flat key→value dict into Notion property objects.
    Strings map to rich_text, numbers to number, booleans to checkbox.
    For titles, the first string field is automatically treated as the title.
    """
    properties: dict[str, Any] = {}
    first_string_key = None

    for key, value in row.items():
        if isinstance(value, bool):
            properties[key] = {"checkbox": value}
        elif isinstance(value, (int, float)):
            properties[key] = {"number": value}
        elif isinstance(value, str):
            if first_string_key is None:
                # Mark first string as a potential title — caller decides the actual field name
                first_string_key = key
            properties[key] = {
                "rich_text": [{"type": "text", "text": {"content": str(value)[:2000]}}]
            }
        else:
            # Fallback: convert to string
            properties[key] = {
                "rich_text": [{"type": "text", "text": {"content": str(value)[:2000]}}]
            }

    return properties


class NotionAppendRowExecutor(BaseExecutor):
    """
    Appends a new page (row) to a Notion database.

    Required params:
        database_id : The Notion database ID (from the database URL)
        row         : Dict of property name → value to write

    Optional params:
        title_field : The name of the title property (default: 'Name')
    """

    async def execute(
        self,
        node: WorkflowNodeDSL,
        context: ExecutionContext,
        resolved_params: dict[str, Any],
    ) -> ExecutorResult:
        database_id = resolved_params.get("database_id") or resolved_params.get("spreadsheet_id", "")
        row = resolved_params.get("row", {})
        title_field = resolved_params.get("title_field", "Name")

        if not database_id:
            return ExecutorResult.fail(
                "'database_id' is required for notion.append_row. "
                "Find it in the Notion database URL: notion.so/<workspace>/<DATABASE_ID>?v=..."
            )
        if not row:
            return ExecutorResult.fail("'row' must be a non-empty dict for notion.append_row.")

        token = _get_notion_token(context)
        if not token:
            return ExecutorResult.fail(
                "Notion integration is not connected or token is missing. "
                "Please reconnect Notion in Settings."
            )

        # ── Build Notion page properties ──────────────────────────────────────
        properties = _build_notion_properties(row)

        # Promote the title field to a 'title' type property
        if title_field in properties:
            title_value = row.get(title_field, "")
            properties[title_field] = {
                "title": [{"type": "text", "text": {"content": str(title_value)[:2000]}}]
            }

        payload = {
            "parent": {"database_id": database_id},
            "properties": properties,
        }

        logger.info(f"[Notion] Appending row to database '{database_id}'")

        # ── Call Notion API ───────────────────────────────────────────────────
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    NOTION_PAGES_URL,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Notion-Version": NOTION_API_VERSION,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            return ExecutorResult.fail(
                f"Notion API HTTP error: {exc.response.status_code} — {exc.response.text}"
            )
        except Exception as exc:
            return ExecutorResult.fail(f"Notion API request failed: {exc}")

        page_id = data.get("id", "")
        page_url = data.get("url", "")
        logger.info(f"[Notion] Row created | page_id={page_id}")

        return ExecutorResult.ok(
            output={
                "page_id": page_id,
                "url": page_url,
                "database_id": database_id,
                "status": "created",
            }
        )
