"""
AutoFlow AI X — Schedule Conflict Check
==========================================
Ensures no two active workflows belonging to the same user share an identical
cron expression. Duplicate cron schedules usually indicate a configuration
mistake and would double-execute the same business logic.

This is a WARNING (not an error) because:
  - Some legitimate use cases exist (e.g. two separate report workflows
    at the same time but with different targets)
  - The user may intentionally want parallel execution
"""

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from backend.database.models import Workflow, WorkflowStatus
from backend.workflow.dsl.schema import WorkflowDSL
from backend.workflow.validator.models import ErrorCode, ValidationResult


def check_schedule_conflict(
    dsl: WorkflowDSL,
    user_id: uuid.UUID,
    db: Session,
    exclude_workflow_id: Optional[uuid.UUID] = None,
) -> ValidationResult:
    """
    Check if another active workflow for the same user has the same cron expression.

    Args:
        dsl                : The workflow DSL being validated
        user_id            : The owning user's ID
        db                 : SQLAlchemy session
        exclude_workflow_id: ID of the workflow being UPDATED (exclude self from conflict check)
    """
    result = ValidationResult()

    # Only relevant for schedule triggers with a cron config
    if dsl.trigger.type.value != "schedule":
        return result

    config = dsl.trigger.config
    cron_expr: Optional[str] = getattr(config, "cron", None)
    if not cron_expr:
        return result

    # Normalize: strip extra whitespace
    cron_expr = " ".join(cron_expr.strip().split())

    # Query active workflows for this user with the same cron expression
    query = (
        db.query(Workflow)
        .filter(
            Workflow.user_id == user_id,
            Workflow.cron_expression == cron_expr,
            Workflow.status == WorkflowStatus.active.value,
            Workflow.deleted_at.is_(None),
        )
    )

    # Exclude the current workflow if we're updating it
    if exclude_workflow_id:
        query = query.filter(Workflow.id != exclude_workflow_id)

    conflicting = query.all()

    if conflicting:
        conflict_names = [f"'{wf.name}'" for wf in conflicting]
        result.add_warning(
            code=ErrorCode.SCHEDULE_CONFLICT,
            message=(
                f"Another active workflow ({', '.join(conflict_names)}) "
                f"already uses cron expression '{cron_expr}'. "
                f"Both will fire at the same time. "
                f"This may be intentional, but verify it isn't a duplicate."
            ),
            detail={
                "cron_expression": cron_expr,
                "conflicting_workflows": [
                    {"id": str(wf.id), "name": wf.name} for wf in conflicting
                ],
            },
        )

    return result
