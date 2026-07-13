"""
AutoFlow AI X — WorkflowValidator
=====================================
The central orchestrator for all pre-save and pre-run validation.

Runs seven checks in sequence:
  1. Schema           — required params, field types, cron format, Slack placeholder channel (Bug #2)
  2. Graph            — reachability + cycle detection
  3. Credentials      — user has connected integrations (DB check)
  4. Templates        — {{variable}} references are valid and ancestral
  5. Schedule         — no cron conflict with other user workflows
  6. Condition keys   — condition expressions reference real output keys (Bug #1)
  7. Routing          — on_success/on_failure agree with edges array (Bug #3)

Design choices:
  - Schema and graph checks run WITHOUT a DB session (pure DSL analysis)
  - Credentials and schedule checks require a DB session
  - All checks run even if earlier checks fail, to surface all issues at once
  - Errors block execution; warnings are advisory
  - Each check returns a ValidationResult that gets merged into the final result
"""

import uuid
import logging
from typing import Optional

from sqlalchemy.orm import Session

from backend.workflow.dsl.schema import WorkflowDSL
from backend.workflow.validator.checks.condition_keys import check_condition_keys
from backend.workflow.validator.checks.credentials import check_credentials
from backend.workflow.validator.checks.graph import check_graph
from backend.workflow.validator.checks.routing_consistency import check_routing_consistency
from backend.workflow.validator.checks.schedule import check_schedule_conflict
from backend.workflow.validator.checks.schema import check_schema
from backend.workflow.validator.checks.templates import check_template_vars
from backend.workflow.validator.models import ValidationResult

logger = logging.getLogger(__name__)


class WorkflowValidator:
    """
    Runs all validation checks against a WorkflowDSL and returns
    a unified ValidationResult.

    Usage:
        validator = WorkflowValidator(db=db)
        result = await validator.validate(
            dsl=dsl,
            user_id=user_id,
            workflow_id=None,   # pass existing ID when updating
        )
        if not result.is_valid:
            return result.to_response()   # {"valid": false, "errors": [...]}
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    async def validate(
        self,
        dsl: WorkflowDSL,
        user_id: uuid.UUID,
        workflow_id: Optional[uuid.UUID] = None,
        skip_credentials: bool = False,
    ) -> ValidationResult:
        """
        Run all validation checks.

        Args:
            dsl               : The workflow DSL to validate
            user_id           : The user who owns this workflow
            workflow_id       : ID of existing workflow (for update — excludes self from conflicts)
            skip_credentials  : Set True in tests or when integrations aren't required
        """
        final = ValidationResult()

        logger.info(
            f"[Validator] Validating workflow '{dsl.name}' for user {user_id} "
            f"({'update' if workflow_id else 'new'})"
        )

        # ── Check 1: Schema ────────────────────────────────────────────────────
        schema_result = check_schema(dsl)
        final.merge(schema_result)
        _log_check("Schema", schema_result)

        # ── Check 2: Graph (reachability + cycles) ─────────────────────────────
        graph_result = check_graph(dsl)
        final.merge(graph_result)
        _log_check("Graph", graph_result)

        # ── Check 3: Credentials (requires DB) ────────────────────────────────
        if not skip_credentials:
            cred_result = check_credentials(dsl, user_id, self.db)
            final.merge(cred_result)
            _log_check("Credentials", cred_result)

        # ── Check 4: Template variables ────────────────────────────────────────
        # Only useful if graph is valid (no cycles) — cycles break topo order
        if not any(e.code == "CYCLE_DETECTED" for e in graph_result.errors):
            tmpl_result = check_template_vars(dsl)
            final.merge(tmpl_result)
            _log_check("Templates", tmpl_result)
        else:
            logger.info("[Validator] Template check skipped (cycle detected in graph).")

        # ── Check 5: Schedule conflict ───────────────────────────────────────────
        sched_result = check_schedule_conflict(
            dsl=dsl,
            user_id=user_id,
            db=self.db,
            exclude_workflow_id=workflow_id,
        )
        final.merge(sched_result)
        _log_check("Schedule", sched_result)

        # ── Check 6: Condition key validation (Bug #1) ────────────────────────────
        # Only useful if graph is valid (need topo order to know which node is upstream)
        if not any(e.code == "CYCLE_DETECTED" for e in graph_result.errors):
            cond_result = check_condition_keys(dsl)
            final.merge(cond_result)
            _log_check("ConditionKeys", cond_result)
        else:
            logger.info("[Validator] Condition key check skipped (cycle detected in graph).")

        # ── Check 7: Routing consistency (Bug #3) ────────────────────────────────
        routing_result = check_routing_consistency(dsl)
        final.merge(routing_result)
        _log_check("RoutingConsistency", routing_result)

        logger.info(
            f"[Validator] Result: {'VALID' if final.is_valid else 'INVALID'} — "
            f"{len(final.errors)} error(s), {len(final.warnings)} warning(s)"
        )
        return final


def _log_check(name: str, result: ValidationResult) -> None:
    if result.errors:
        logger.warning(f"[Validator] {name}: {len(result.errors)} error(s)")
    elif result.warnings:
        logger.info(f"[Validator] {name}: {len(result.warnings)} warning(s)")
    else:
        logger.debug(f"[Validator] {name}: OK")
