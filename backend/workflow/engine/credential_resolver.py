"""
AutoFlow AI X — Credential Resolver  (RFC-001 §8)
===================================================
Single point of credential resolution for all executors.

Before each node executes, the WorkflowRunner calls:
    resolver.resolve_for_node(node, context)

This populates context._secrets[service_name] with the decrypted
credentials dict so executors can call context.get_secret("slack")
instead of each doing their own DB query.

Design decisions:
  - Per-run in-memory cache keyed by service name (and credential_id when set).
    A cold DB query happens at most once per service per run.
  - Executors that don't need credentials (builtin ops, set_variable, etc.)
    are skipped via CREDENTIAL_FREE_SERVICES.
  - credential_id (Sprint 2 Node Inspector) takes priority over service-name
    lookup when present.
  - If an integration is not connected, the secret slot stays empty.
    The executor is responsible for returning ExecutorResult.fail() if it needs
    a credential that wasn't resolved (same behaviour as before).
"""

import logging
from typing import TYPE_CHECKING, Optional

from backend.integrations.service import decrypt_credentials

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from backend.workflow.engine.context import ExecutionContext
    from backend.workflow.dsl.schema import WorkflowNodeDSL

logger = logging.getLogger(__name__)

# Services that never need a credential lookup.
CREDENTIAL_FREE_SERVICES = frozenset(
    {
        "builtin",
        "scheduler",
        "http",       # HTTP executor uses params.headers for auth (no OAuth)
    }
)


class CredentialResolver:
    """
    Resolves integration credentials for a single workflow run.

    Usage (called by WorkflowRunner before each node):
        resolver.resolve_for_node(node, context)
        # → context.get_secret("slack") returns the decrypted creds dict

    Thread safety: each WorkflowRunner instantiates its own resolver,
    so the cache is isolated per run.
    """

    def __init__(self, db: "Session") -> None:
        self._db = db
        # Cache: cache_key → decrypted creds dict.
        # Key is credential_id when set, otherwise service_name.
        self._cache: dict[str, dict] = {}

    # ── Public API ────────────────────────────────────────────────────────────

    def resolve_for_node(
        self,
        node: "WorkflowNodeDSL",
        context: "ExecutionContext",
    ) -> None:
        """
        Look up credentials for the node's service and populate context.secrets.

        If credentials are already in the run-level cache, the DB is not hit again.
        If no integration is found, logs a warning and leaves the slot empty —
        the executor will surface the missing-credential error at runtime.
        """
        service_name = node.service.value if node.service else None
        if not service_name or service_name in CREDENTIAL_FREE_SERVICES:
            return

        # Prefer explicit credential_id; fall back to service-name resolution.
        credential_id: Optional[str] = getattr(node, "credential_id", None)
        cache_key = credential_id if credential_id else service_name

        if cache_key in self._cache:
            context.set_secret(service_name, self._cache[cache_key])
            return

        creds = self._fetch(service_name, context.user_id, credential_id)
        if creds is not None:
            self._cache[cache_key] = creds
            context.set_secret(service_name, creds)
        else:
            logger.warning(
                "[CredentialResolver] No active '%s' integration found for user %s. "
                "Executor will handle missing credential.",
                service_name,
                context.user_id,
            )

    # ── Internal ──────────────────────────────────────────────────────────────

    def _fetch(
        self,
        service_name: str,
        user_id,
        credential_id: Optional[str],
    ) -> Optional[dict]:
        """
        Query the Integration table and decrypt the credentials blob.
        Returns the decrypted dict, or None if no matching integration exists.
        """
        try:
            from backend.database.models import Integration, IntegrationService

            query = self._db.query(Integration).filter(
                Integration.user_id == user_id,
                Integration.is_active == True,  # noqa: E712
            )

            if credential_id:
                # Sprint 2: look up by explicit UUID when the DSL node has one
                import uuid as _uuid
                query = query.filter(
                    Integration.id == _uuid.UUID(credential_id)
                )
            else:
                # Sprint 1: resolve by service name (one active cred per service)
                google_suite_names = {"gmail", "google_sheets", "google_calendar", "google_drive", "google"}
                if service_name in google_suite_names:
                    query = query.filter(Integration.service_name.in_([
                        IntegrationService.gmail,
                        IntegrationService.google_sheets,
                        IntegrationService.google_calendar,
                        IntegrationService.google_drive,
                    ]))
                else:
                    try:
                        svc_enum = IntegrationService(service_name)
                    except ValueError:
                        logger.debug(
                            "[CredentialResolver] '%s' is not a known IntegrationService — skipping.",
                            service_name,
                        )
                        return None
                    query = query.filter(Integration.service_name == svc_enum)

            integration = query.first()
            if not integration:
                return None

            return decrypt_credentials(integration.credentials_encrypted)

        except Exception as exc:
            logger.error(
                "[CredentialResolver] Failed to fetch credential for '%s': %s",
                service_name,
                exc,
                exc_info=True,
            )
            return None
