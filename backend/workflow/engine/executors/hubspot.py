"""
AutoFlow AI X — HubSpot CRM Executor
======================================
Handles HubSpot CRM v3 operations:
  - append_row : Create (or upsert on 409 conflict) a contact, deal, or company
  - update_row : Update an existing CRM record by ID (or by email for contacts)
  - find_row   : Search CRM records using HubSpot filterGroups

Auth flow:
  - Supports both HubSpot Private App Access Tokens (`pat-...`) and OAuth 2.0.
  - Automatically refreshes expired OAuth access tokens when `refresh_token`,
    `HUBSPOT_CLIENT_ID`, and `HUBSPOT_CLIENT_SECRET` are available.
  - Falls back to `HUBSPOT_ACCESS_TOKEN` environment variable if configured.
"""

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

import httpx

from backend.workflow.dsl.schema import WorkflowNodeDSL
from backend.workflow.engine.context import ExecutionContext
from backend.workflow.engine.executors.base import BaseExecutor, ExecutorResult

logger = logging.getLogger(__name__)

HUBSPOT_BASE_URL = "https://api.hubapi.com/crm/v3/objects"
HUBSPOT_TOKEN_URL = "https://api.hubapi.com/oauth/v1/token"

_DIRECT_CRM_FIELDS = (
    "email",
    "firstname",
    "lastname",
    "phone",
    "company",
    "website",
    "jobtitle",
    "lifecyclestage",
    "hs_lead_status",
    "dealname",
    "amount",
    "dealstage",
    "pipeline",
    "closedate",
    "name",
    "domain",
    "industry",
    "city",
    "state",
    "country",
)

_EXISTING_ID_RE = re.compile(r"Existing ID:\s*(\d+)", re.IGNORECASE)


def _get_hubspot_token(context: ExecutionContext) -> str | None:
    """Retrieve the HubSpot access token from context secrets, DB credentials, or environment."""
    # 1. Check pre-resolved context secret
    if hasattr(context, "get_secret"):
        secret = context.get_secret("hubspot")
        if isinstance(secret, dict) and secret.get("access_token"):
            return str(secret["access_token"]).strip()
        if isinstance(secret, str) and secret.strip():
            return secret.strip()

    # 2. Check encrypted database integration for the user
    try:
        from backend.database.models import Integration, IntegrationService
        from backend.integrations.service import decrypt_credentials

        db = context.db
        user_id = context.user_id

        if db is not None and user_id is not None:
            integration = (
                db.query(Integration)
                .filter(
                    Integration.user_id == user_id,
                    Integration.service_name == IntegrationService.hubspot,
                    Integration.is_active == True,
                )
                .first()
            )
            if integration:
                creds = decrypt_credentials(integration.credentials_encrypted)
                token = creds.get("access_token")
                if token:
                    return str(token).strip()
    except Exception as exc:
        logger.error(f"[HubSpot] Failed to retrieve token from DB: {exc}", exc_info=True)

    # 3. Check environment variable fallback
    env_token = os.getenv("HUBSPOT_ACCESS_TOKEN", "").strip()
    if env_token:
        return env_token

    return None


async def _try_refresh_hubspot_token(context: ExecutionContext) -> str | None:
    """If an OAuth refresh_token is stored, exchange it for a fresh access_token."""
    try:
        from backend.database.models import Integration, IntegrationService
        from backend.integrations.service import decrypt_credentials, encrypt_credentials, get_provider_redirect_uri

        db = context.db
        user_id = context.user_id
        if db is None or user_id is None:
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
            return None

        creds = decrypt_credentials(integration.credentials_encrypted)
        refresh_token = creds.get("refresh_token")
        client_id = os.getenv("HUBSPOT_CLIENT_ID", "").strip()
        client_secret = os.getenv("HUBSPOT_CLIENT_SECRET", "").strip()
        if not refresh_token or not client_id or not client_secret:
            return None

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                HUBSPOT_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": get_provider_redirect_uri("hubspot"),
                    "refresh_token": refresh_token,
                },
            )
        if resp.is_error:
            logger.warning(f"[HubSpot] OAuth token refresh failed: HTTP {resp.status_code}")
            return None

        token_data = resp.json()
        new_access_token = token_data.get("access_token")
        if not new_access_token:
            return None

        creds["access_token"] = new_access_token
        if token_data.get("refresh_token"):
            creds["refresh_token"] = token_data["refresh_token"]
        integration.credentials_encrypted = encrypt_credentials(creds)
        integration.last_synced_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("[HubSpot] Refreshed OAuth access_token successfully.")
        return str(new_access_token).strip()
    except Exception as exc:
        logger.warning(f"[HubSpot] Error refreshing token: {exc}")
        return None


def _extract_hubspot_properties(resolved_params: dict[str, Any]) -> dict[str, Any]:
    """
    Extract HubSpot property dictionary from `row`, `properties`, or flat top-level params.
    Accepts dicts or JSON-encoded strings.
    """
    raw = resolved_params.get("row") or resolved_params.get("properties")
    props: dict[str, Any] = {}

    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                props.update(parsed)
        except json.JSONDecodeError:
            pass
    elif isinstance(raw, dict):
        props.update(raw)

    for key in _DIRECT_CRM_FIELDS:
        val = resolved_params.get(key)
        if val is not None and val != "" and key not in props:
            props[key] = val

    # Clean None values and convert primitives to HubSpot-compatible strings/numbers
    cleaned: dict[str, Any] = {}
    for k, v in props.items():
        if v is None:
            continue
        cleaned[str(k)] = v
    return cleaned


async def _hubspot_request(
    method: str,
    url: str,
    token: str,
    context: ExecutionContext,
    json_payload: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> httpx.Response:
    """Execute an authenticated HubSpot API request with automatic OAuth refresh on 401."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.request(method, url, headers=headers, json=json_payload, params=params)
        if resp.status_code == 401:
            refreshed = await _try_refresh_hubspot_token(context)
            if refreshed:
                headers["Authorization"] = f"Bearer {refreshed}"
                resp = await client.request(method, url, headers=headers, json=json_payload, params=params)
        return resp


class HubSpotAppendRowExecutor(BaseExecutor):
    """
    Creates (or upserts on 409 conflict) a CRM record (contact, deal, company) in HubSpot.

    Required params:
        row         : Dict of HubSpot property name → value (or top-level CRM fields)

    Optional params:
        object_type : HubSpot object type — 'contacts' (default), 'deals', 'companies'
    """

    async def execute(
        self,
        node: WorkflowNodeDSL,
        context: ExecutionContext,
        resolved_params: dict[str, Any],
    ) -> ExecutorResult:
        row = _extract_hubspot_properties(resolved_params)
        object_type = (resolved_params.get("object_type") or "contacts").strip().lower()

        if not row:
            return ExecutorResult.fail(
                "'row' (or CRM property fields like 'email', 'firstname') must be non-empty for hubspot.append_row."
            )

        token = _get_hubspot_token(context)
        if not token:
            return ExecutorResult.fail(
                "HubSpot CRM integration is not connected or token is missing. "
                "Please connect HubSpot in Settings."
            )

        payload = {"properties": row}
        url = f"{HUBSPOT_BASE_URL}/{object_type}"

        logger.info(f"[HubSpot] Creating {object_type} record | properties={list(row.keys())}")

        try:
            resp = await _hubspot_request("POST", url, token, context, json_payload=payload)

            # Upsert handling: if contact already exists (HTTP 409), update existing record seamlessly
            if resp.status_code == 409:
                body_text = resp.text
                match = _EXISTING_ID_RE.search(body_text)
                existing_id = match.group(1) if match else None

                if existing_id:
                    patch_url = f"{HUBSPOT_BASE_URL}/{object_type}/{existing_id}"
                    patch_resp = await _hubspot_request("PATCH", patch_url, token, context, json_payload=payload)
                    if not patch_resp.is_error:
                        patch_data = patch_resp.json()
                        logger.info(f"[HubSpot] {object_type} '{existing_id}' already existed — updated properties.")
                        return ExecutorResult.ok(
                            output={
                                "id": str(existing_id),
                                "object_type": object_type,
                                "properties": patch_data.get("properties", row),
                                "status": "updated_existing",
                            }
                        )
                    return ExecutorResult.ok(
                        output={
                            "id": str(existing_id),
                            "object_type": object_type,
                            "properties": row,
                            "status": "existing",
                        }
                    )

            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            return ExecutorResult.fail(
                f"HubSpot API HTTP error ({exc.response.status_code}): {exc.response.text[:300]}"
            )
        except Exception as exc:
            return ExecutorResult.fail(f"HubSpot API request failed: {exc}")

        record_id = str(data.get("id", ""))
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
    Updates an existing CRM record in HubSpot by record_id (or by email for contacts).

    Required params:
        record_id   : HubSpot record ID (or contact email address) to update
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
        record_id = str(
            resolved_params.get("record_id")
            or resolved_params.get("id")
            or resolved_params.get("email")
            or ""
        ).strip()
        row = _extract_hubspot_properties(resolved_params)
        object_type = (resolved_params.get("object_type") or "contacts").strip().lower()

        if not record_id:
            return ExecutorResult.fail("'record_id' is required for hubspot.update_row.")
        if not row:
            return ExecutorResult.fail("'row' must be a non-empty dict for hubspot.update_row.")

        token = _get_hubspot_token(context)
        if not token:
            return ExecutorResult.fail("HubSpot CRM integration is not connected. Reconnect in Settings.")

        url = f"{HUBSPOT_BASE_URL}/{object_type}/{record_id}"
        query_params = {"idProperty": "email"} if ("@" in record_id and object_type == "contacts") else None
        payload = {"properties": row}

        logger.info(f"[HubSpot] Updating {object_type} record '{record_id}'")

        try:
            resp = await _hubspot_request("PATCH", url, token, context, json_payload=payload, params=query_params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            return ExecutorResult.fail(
                f"HubSpot API HTTP error ({exc.response.status_code}): {exc.response.text[:300]}"
            )
        except Exception as exc:
            return ExecutorResult.fail(f"HubSpot API request failed: {exc}")

        logger.info(f"[HubSpot] {object_type} '{record_id}' updated.")

        return ExecutorResult.ok(
            output={
                "id": str(data.get("id", record_id)),
                "object_type": object_type,
                "properties": data.get("properties", {}),
                "status": "updated",
            }
        )


class HubSpotFindRowExecutor(BaseExecutor):
    """
    Searches for CRM records in HubSpot using filter criteria.

    Required params:
        filter_value    : Value to match

    Optional params:
        filter_property : Property name to filter on (default: 'email')
        object_type     : 'contacts' (default), 'deals', 'companies'
        properties      : List of property names to return
    """

    async def execute(
        self,
        node: WorkflowNodeDSL,
        context: ExecutionContext,
        resolved_params: dict[str, Any],
    ) -> ExecutorResult:
        filter_property = (resolved_params.get("filter_property") or "email").strip()
        filter_value = str(
            resolved_params.get("filter_value")
            or resolved_params.get("email")
            or resolved_params.get("query")
            or ""
        ).strip()
        object_type = (resolved_params.get("object_type") or "contacts").strip().lower()
        properties = resolved_params.get(
            "properties",
            ["email", "firstname", "lastname", "company", "phone", "lifecyclestage"],
        )
        if isinstance(properties, str):
            properties = [p.strip() for p in properties.split(",") if p.strip()]

        if not filter_value:
            return ExecutorResult.fail("'filter_value' is required for hubspot.find_row.")

        token = _get_hubspot_token(context)
        if not token:
            return ExecutorResult.fail("HubSpot CRM integration is not connected. Reconnect in Settings.")

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
            resp = await _hubspot_request("POST", url, token, context, json_payload=payload)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            return ExecutorResult.fail(
                f"HubSpot API HTTP error ({exc.response.status_code}): {exc.response.text[:300]}"
            )
        except Exception as exc:
            return ExecutorResult.fail(f"HubSpot API request failed: {exc}")

        results = data.get("results", [])
        first_record = results[0] if results else None
        logger.info(f"[HubSpot] Found {len(results)} {object_type} matching the filter.")

        return ExecutorResult.ok(
            output={
                "results": results,
                "count": len(results),
                "total": data.get("total", len(results)),
                "first_id": str(first_record.get("id", "")) if first_record else "",
                "first_properties": first_record.get("properties", {}) if first_record else {},
            }
        )
