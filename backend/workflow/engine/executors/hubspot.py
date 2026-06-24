"""
AutoFlow AI X — HubSpot Executor
===================================
Handles HubSpot CRM operations: append_row (create contact/deal),
update_row (update a record), find_row (search contacts).

Auth flow:
  - User connects HubSpot via OAuth (integrations layer).
  - access_token stored encrypted in integrations table.
  - HubSpot CRM v3 API — https://developers.hubspot.com/docs/api/crm/contacts

Object type defaults to 'contacts' — DSL can override with 'object_type' param.
"""

import logging
from typing import Any

import httpx

from backend.workflow.dsl.schema import WorkflowNodeDSL
from backend.workflow.engine.context import ExecutionContext
from backend.workflow.engine.executors.base import BaseExecutor, ExecutorResult

logger = logging.getLogger(__name__)

HUBSPOT_BASE_URL = "https://api.hubapi.com/crm/v3/objects"


def _get_hubspot_token(context: ExecutionContext) -> str | None:
    """Retrieve the HubSpot access token from the user's stored credentials."""
    try:
        from backend.integrations.service import decrypt_credentials
        from backend.database.models import Integration, IntegrationService

        db = context.db
        user_id = context.user_id

        if db is None or user_id is None:
            logger.warning("[HubSpot] No DB session or user_id in context.")
            return None

        integration = (
            db.query(Integration)
            .filter(
                Integration.user_id == user_id,
                Integration.service_name == IntegrationService.hubspot,
                Integration.is_active == True,
            )
            .first()
        )

        if not integration:
            logger.warning(f"[HubSpot] No active HubSpot integration found for user {user_id}.")
            return None

        creds = decrypt_credentials(integration.credentials_encrypted)
        return creds.get("access_token")

    except Exception as exc:
        logger.error(f"[HubSpot] Failed to retrieve token: {exc}", exc_info=True)
        return None


class HubSpotAppendRowExecutor(BaseExecutor):
    """
    Creates a new CRM record (contact, deal, company, etc.) in HubSpot.

    Required params:
        row         : Dict of HubSpot property name → value

    Optional params:
        object_type : HubSpot object type — 'contacts' (default), 'deals', 'companies'
    """

    async def execute(
        self,
        node: WorkflowNodeDSL,
        context: ExecutionContext,
        resolved_params: dict[str, Any],
    ) -> ExecutorResult:
        row = resolved_params.get("row", {})
        object_type = resolved_params.get("object_type", "contacts")

        if not row:
            return ExecutorResult.fail("'row' must be a non-empty dict for hubspot.append_row.")

        token = _get_hubspot_token(context)
        if not token:
            return ExecutorResult.fail(
                "HubSpot integration is not connected or token is missing. "
                "Please reconnect HubSpot in Settings."
            )

        payload = {"properties": row}
        url = f"{HUBSPOT_BASE_URL}/{object_type}"

        logger.info(f"[HubSpot] Creating {object_type} record | properties={list(row.keys())}")

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            return ExecutorResult.fail(
                f"HubSpot API HTTP error: {exc.response.status_code} — {exc.response.text}"
            )
        except Exception as exc:
            return ExecutorResult.fail(f"HubSpot API request failed: {exc}")

        record_id = data.get("id", "")
        logger.info(f"[HubSpot] {object_type} created | id={record_id}")

        return ExecutorResult.ok(
            output={
                "id": record_id,
                "object_type": object_type,
                "properties": data.get("properties", {}),
                "status": "created",
            }
        )


class HubSpotUpdateRowExecutor(BaseExecutor):
    """
    Updates an existing CRM record in HubSpot.

    Required params:
        record_id   : HubSpot record ID to update
        row         : Dict of property name → new value

    Optional params:
        object_type : 'contacts' (default), 'deals', 'companies'
    """

    async def execute(
        self,
        node: WorkflowNodeDSL,
        context: ExecutionContext,
        resolved_params: dict[str, Any],
    ) -> ExecutorResult:
        record_id = resolved_params.get("record_id") or resolved_params.get("id", "")
        row = resolved_params.get("row", {})
        object_type = resolved_params.get("object_type", "contacts")

        if not record_id:
            return ExecutorResult.fail("'record_id' is required for hubspot.update_row.")
        if not row:
            return ExecutorResult.fail("'row' must be a non-empty dict for hubspot.update_row.")

        token = _get_hubspot_token(context)
        if not token:
            return ExecutorResult.fail("HubSpot integration is not connected. Reconnect in Settings.")

        url = f"{HUBSPOT_BASE_URL}/{object_type}/{record_id}"
        payload = {"properties": row}

        logger.info(f"[HubSpot] Updating {object_type} record '{record_id}'")

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.patch(
                    url,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            return ExecutorResult.fail(
                f"HubSpot API HTTP error: {exc.response.status_code} — {exc.response.text}"
            )
        except Exception as exc:
            return ExecutorResult.fail(f"HubSpot API request failed: {exc}")

        logger.info(f"[HubSpot] {object_type} '{record_id}' updated.")

        return ExecutorResult.ok(
            output={
                "id": data.get("id", record_id),
                "object_type": object_type,
                "properties": data.get("properties", {}),
                "status": "updated",
            }
        )


class HubSpotFindRowExecutor(BaseExecutor):
    """
    Searches for CRM records in HubSpot using filter criteria.

    Required params:
        filter_property : Property name to filter on (e.g. 'email')
        filter_value    : Value to match

    Optional params:
        object_type     : 'contacts' (default), 'deals', 'companies'
        properties      : List of property names to return
    """

    async def execute(
        self,
        node: WorkflowNodeDSL,
        context: ExecutionContext,
        resolved_params: dict[str, Any],
    ) -> ExecutorResult:
        filter_property = resolved_params.get("filter_property", "email")
        filter_value = resolved_params.get("filter_value", "")
        object_type = resolved_params.get("object_type", "contacts")
        properties = resolved_params.get("properties", ["email", "firstname", "lastname"])

        if not filter_value:
            return ExecutorResult.fail("'filter_value' is required for hubspot.find_row.")

        token = _get_hubspot_token(context)
        if not token:
            return ExecutorResult.fail("HubSpot integration is not connected. Reconnect in Settings.")

        url = f"{HUBSPOT_BASE_URL}/{object_type}/search"
        payload = {
            "filterGroups": [{
                "filters": [{
                    "propertyName": filter_property,
                    "operator": "EQ",
                    "value": filter_value,
                }]
            }],
            "properties": properties if isinstance(properties, list) else [properties],
            "limit": 10,
        }

        logger.info(f"[HubSpot] Searching {object_type} where {filter_property}='{filter_value}'")

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            return ExecutorResult.fail(
                f"HubSpot API HTTP error: {exc.response.status_code} — {exc.response.text}"
            )
        except Exception as exc:
            return ExecutorResult.fail(f"HubSpot API request failed: {exc}")

        results = data.get("results", [])
        logger.info(f"[HubSpot] Found {len(results)} {object_type} matching the filter.")

        return ExecutorResult.ok(
            output={
                "results": results,
                "count": len(results),
                "total": data.get("total", len(results)),
            }
        )
