"""
AutoFlow AI X — Celery Tasks (LangGraph Edition)
==================================================
All Celery task definitions.

Key change from v1:
  WorkflowRunner is replaced by LangGraphRuntime, which:
    - Auto-uses LangGraph StateGraph for workflows with ai_agent nodes
    - Falls back to WorkflowRunner for simple executor-only workflows
    - Fully backward compatible — no DSL changes needed
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from celery import states
from celery.exceptions import Ignore

from backend.workers.celery_app import celery_app
from backend.database.session import SessionLocal
from backend.database.models import RunStatus, Workflow, WorkflowRun
from backend.workflow.dsl.schema import WorkflowDSL
# LangGraphRuntime replaces WorkflowRunner — auto-selects runtime based on DSL
from backend.workflow.langgraph_engine.runtime import LangGraphRuntime

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _get_db_session():
    return SessionLocal()


def _mark_run_failed(db, run_id: uuid.UUID, error: str) -> None:
    try:
        run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
        if run:
            run.status        = RunStatus.failed.value
            run.finished_at   = _utcnow()
            run.error_message = str(error)[:2000]
            db.commit()
    except Exception as e:
        logger.error(f"[Task] Failed to mark run {run_id} FAILED: {e}")
        try: db.rollback()
        except Exception: pass


# ─────────────────────────────────────────────────────────────────────────────
# Task: run_workflow_task
# ─────────────────────────────────────────────────────────────────────────────

@celery_app.task(
    name="autoflow.run_workflow",
    bind=True,
    max_retries=3,
    queue="default",
    acks_late=True,
    track_started=True,
    soft_time_limit=600,
    time_limit=660,
)
def run_workflow_task(self, *, run_id: str, workflow_id: str, trigger_payload: dict = None) -> dict:
    """
    Execute a workflow using LangGraphRuntime (which auto-selects LangGraph or simple runner).
    Retry on failure with exponential backoff: 1s, 2s, 4s.
    """
    _run_id      = uuid.UUID(run_id)
    _workflow_id = uuid.UUID(workflow_id)
    trigger_payload = trigger_payload or {}

    self.update_state(state=states.STARTED, meta={"run_id": run_id, "status": "running"})

    db = _get_db_session()
    try:
        workflow = db.query(Workflow).filter(Workflow.id == _workflow_id).first()
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found in DB.")

        dsl_json = workflow.ai_context_json
        if not dsl_json:
            raise ValueError(f"Workflow {workflow_id} has no DSL.")

        dsl = WorkflowDSL.model_validate(dsl_json)

        # Mark run as running + store Celery task ID
        run = db.query(WorkflowRun).filter(WorkflowRun.id == _run_id).first()
        if run:
            run.status         = RunStatus.running.value
            run.started_at     = _utcnow()
            run.celery_task_id = self.request.id
            db.commit()

        # ── LangGraphRuntime (replaces WorkflowRunner) ────────────────────────
        runtime = LangGraphRuntime(
            dsl             = dsl,
            run_id          = _run_id,
            db              = db,
            trigger_payload = trigger_payload,
        )
        asyncio.run(runtime.run())

        db.refresh(run)
        return {
            "run_id":      run_id,
            "workflow_id": workflow_id,
            "status":      run.status,
            "duration_ms": run.duration_ms,
            "runtime":     "langgraph" if any(n.type.value == "ai_agent" for n in dsl.nodes) else "simple",
        }

    except Exception as exc:
        logger.error(
            f"[Task] run_workflow_task failed for run {run_id}, "
            f"attempt {self.request.retries + 1}/{self.max_retries + 1}: {exc}",
            exc_info=True,
        )
        countdown = 2 ** self.request.retries  # 1, 2, 4 seconds
        if self.request.retries < self.max_retries:
            try:
                run = db.query(WorkflowRun).filter(WorkflowRun.id == _run_id).first()
                if run:
                    run.status         = RunStatus.retrying.value
                    run.attempt_number = self.request.retries + 2
                    db.commit()
            except Exception: pass
            raise self.retry(exc=exc, countdown=countdown)
        else:
            _mark_run_failed(db, _run_id, str(exc))
            raise
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Task: run_scheduled_workflow (Beat → dispatch run_workflow_task)
# ─────────────────────────────────────────────────────────────────────────────

@celery_app.task(
    name="autoflow.run_scheduled_workflow",
    bind=True,
    max_retries=2,
    queue="scheduled",
    acks_late=True,
    track_started=True,
    soft_time_limit=600,
    time_limit=660,
)
def run_scheduled_workflow(self, *, workflow_id: str) -> dict:
    """Entry point for Beat-scheduled workflows. Creates a WorkflowRun and dispatches."""
    _workflow_id = uuid.UUID(workflow_id)
    db = _get_db_session()
    try:
        workflow = db.query(Workflow).filter(Workflow.id == _workflow_id).first()
        if not workflow:
            logger.warning(f"[Beat] Scheduled workflow {workflow_id} not found.")
            self.update_state(state=states.IGNORED)
            raise Ignore()

        if workflow.status != "active":
            logger.info(f"[Beat] Workflow {workflow_id} is not active. Skipping.")
            self.update_state(state=states.IGNORED)
            raise Ignore()

        run_id = uuid.uuid4()
        run = WorkflowRun(
            id              = run_id,
            workflow_id     = _workflow_id,
            user_id         = workflow.user_id,
            status          = RunStatus.pending.value,
            trigger_type    = "schedule",
            trigger_payload = {},
            attempt_number  = 1,
            max_attempts    = 3,
        )
        db.add(run)
        db.commit()

        run_workflow_task.apply_async(
            kwargs={
                "run_id":          str(run_id),
                "workflow_id":     workflow_id,
                "trigger_payload": {},
            },
            queue="default",
        )

        logger.info(f"[Beat] Scheduled run {run_id} dispatched for '{workflow.name}'")
        return {"run_id": str(run_id), "workflow_id": workflow_id}

    except Ignore:
        raise
    except Exception as exc:
        logger.error(f"[Beat] Failed to schedule {workflow_id}: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
    finally:
        db.close()
