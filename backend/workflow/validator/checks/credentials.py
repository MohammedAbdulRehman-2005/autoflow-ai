"""
AutoFlow AI X — Credential Validation Check
=============================================
For each node that requires an external service, verify that the
current user has a connected integration for that service in the DB.

The `integrations` table stores one row per connected service per user.
If the row doesn't exist (or `credentials_encrypted` is null), the
workflow cannot run.

Services that do NOT need credentials (use env vars or no auth):
  - builtin, scheduler, http, groq, openai
"""

import uuid
from sqlalchemy.orm import Session

from backend.database.models import Integration
from backend.workflow.dsl.schema import ServiceType, WorkflowDSL
from backend.workflow.validator.models import ErrorCode, ValidationResult

# ─────────────────────────────────────────────────────────────────────────────
# Services that require a user-connected integration in the DB
# Maps ServiceType → human-readable integration name
# ─────────────────────────────────────────────────────────────────────────────
CREDENTIAL_REQUIRED_SERVICES: dict[str, str] = {
    ServiceType.gmail.value:            "Gmail",
    ServiceType.google_sheets.value:    "Google Sheets",
    ServiceType.google_calendar.value:  "Google Calendar",
    ServiceType.google_drive.value:     "Google Drive",
    ServiceType.whatsapp.value:         "WhatsApp",
    ServiceType.slack.value:            "Slack",
    ServiceType.twilio.value:           "Twilio",
    ServiceType.hubspot.value:          "HubSpot",
    ServiceType.salesforce.value:       "Salesforce",
    ServiceType.notion.value:           "Notion",
    ServiceType.airtable.value:         "Airtable",
}

# Services that are credential-free (env vars or no auth needed)
CREDENTIAL_FREE_SERVICES: set[str] = {
    ServiceType.builtin.value,
    ServiceType.scheduler.value,
    ServiceType.http.value,
    ServiceType.groq.value,
    ServiceType.openai.value,
}


def check_credentials(
    dsl: WorkflowDSL,
    user_id: uuid.UUID,
    db: Session,
) -> ValidationResult:
    """
    For each node using an external service, check that the user has
    a connected integration in the `integrations` DB table.

    Caching: we query once per unique service to avoid N+1 queries.
    """
    result = ValidationResult()

    # Collect unique services that need credentials (skip triggers + disabled)
    services_needed: dict[str, list[str]] = {}  # service_name → [node_ids]
    for node in dsl.nodes:
        if node.is_disabled:
            continue
        svc = node.service.value
        if svc in CREDENTIAL_REQUIRED_SERVICES:
            services_needed.setdefault(svc, []).append(node.id)

    if not services_needed:
        return result  # No credentials needed

    # Query all integrations for this user in one hit
    connected_services = {
        row.service_name.value if hasattr(row.service_name, "value") else str(row.service_name)
        for row in db.query(Integration.service_name)
        .filter(
            Integration.user_id == user_id,
            Integration.credentials_encrypted.isnot(None),
        )
        .all()
    }

    # Google OAuth covers all Google services
    google_suite = {"gmail", "google_sheets", "google_calendar", "google_drive", "google"}
    if connected_services & google_suite:
        connected_services.update(google_suite)

    # Compare needed vs connected
    for service_name, node_ids in services_needed.items():
        human_name = CREDENTIAL_REQUIRED_SERVICES[service_name]
        if service_name not in connected_services:
            # Report the error on EACH node that needs this service
            for node_id in node_ids:
                node = next(n for n in dsl.nodes if n.id == node_id)
                # Downgraded to WARNING: missing credentials block *execution*
                # but should not prevent *saving* a workflow draft.
                result.add_warning(
                    code=ErrorCode.MISSING_CREDENTIAL,
                    node_id=node_id,
                    message=(
                        f"Node '{node.label}' requires {human_name} but you haven't "
                        f"connected {human_name} yet. "
                        f"Go to Settings → Integrations to connect it before running."
                    ),
                    detail={
                        "service": service_name,
                        "integration_name": human_name,
                        "connect_url": f"/settings/integrations/{service_name}",
                    },
                )

    return result
