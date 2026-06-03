"""
AutoFlow AI X — Scheduled Job Executor
========================================
Top-level module functions that APScheduler calls when a cron fires.

CRITICAL: These MUST be module-level functions (not lambdas, closures, or methods)
because APScheduler serializes them by reference (module path + name) in the
SQLAlchemy job store. If they're nested or anonymous, jobs won't survive restarts.
"""

import logging
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def execute_scheduled_workflow(workflow_id_str: str) -> None:
    """
    APScheduler entry point for a scheduled workflow execution.

    Creates a fresh SQLAlchemy session (never reuse sessions across threads/tasks),
    loads the workflow DSL, creates a WorkflowRun record, and fires the engine.

    Args:
        workflow_id_str: UUID string of the workflow to execute.
    """
    # Deferred imports to avoid circular dependencies at module load time
    from backend.database.session import SessionLocal
    from backend.database.models import RunStatus, Workflow, WorkflowRun
    from backend.workflow.dsl.schema import WorkflowDSL
    from backend.workflow.engine.runner import WorkflowRunner

    workflow_id = uuid.UUID(workflow_id_str)
    db = SessionLocal()

    logger.info(f"[Scheduler] Cron fired for workflow {workflow_id}")

    try:
        # 1. Load the workflow
        workflow = (
            db.query(Workflow)
            .filter(
                Workflow.id == workflow_id,
                Workflow.deleted_at.is_(None),
            )
            .first()
        )

        if not workflow:
            logger.warning(f"[Scheduler] Workflow {workflow_id} not found. Skipping.")
            return

        if not workflow.ai_context_json:
            logger.warning(f"[Scheduler] Workflow {workflow_id} has no DSL. Skipping.")
            return

        # 2. Parse DSL
        try:
            dsl = WorkflowDSL.model_validate(workflow.ai_context_json)
        except Exception as e:
            logger.error(f"[Scheduler] Invalid DSL for workflow {workflow_id}: {e}")
            return

        # 3. Create run record
        run_id = uuid.uuid4()
        run = WorkflowRun(
            id=run_id,
            workflow_id=workflow.id,
            user_id=workflow.user_id,
            status=RunStatus.pending.value,
            trigger_type="scheduled",
            trigger_payload={
                "triggered_by": "scheduler",
                "triggered_at": datetime.now(timezone.utc).isoformat(),
                "cron_expression": workflow.cron_expression,
            },
            attempt_number=1,
            max_attempts=3,
        )
        db.add(run)
        db.commit()

        logger.info(
            f"[Scheduler] Starting run {run_id} for workflow '{workflow.name}'"
        )

        # 4. Execute workflow
        runner = WorkflowRunner(
            dsl=dsl,
            run_id=run_id,
            db=db,
            trigger_payload={"cron_expression": workflow.cron_expression},
        )
        await runner.run()

        logger.info(f"[Scheduler] Run {run_id} completed for workflow '{workflow.name}'")

    except Exception as e:
        logger.error(
            f"[Scheduler] Scheduled execution failed for workflow {workflow_id}: {e}",
            exc_info=True,
        )
    finally:
        db.close()
