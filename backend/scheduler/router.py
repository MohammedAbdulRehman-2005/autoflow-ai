"""
AutoFlow AI X — Scheduler API Router
======================================
Endpoints for managing workflow schedules.

POST   /workflows/{id}/schedule    → Create or update a workflow's schedule
DELETE /workflows/{id}/schedule    → Remove a workflow's schedule
PATCH  /workflows/{id}/schedule/pause  → Pause without removing
PATCH  /workflows/{id}/schedule/resume → Resume a paused schedule
GET    /workflows/scheduled         → List all scheduled workflows + next_run_time
GET    /workflows/{id}/next-run     → Get next run time for one workflow
"""

import uuid
import logging
from typing import Annotated, Union

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.database.models import User, Workflow
from backend.database.session import get_db
from backend.scheduler.schemas import (
    CronSchedule,
    IntervalSchedule,
    OnceSchedule,
    ScheduleResponse,
    ScheduledListResponse,
    ScheduledWorkflow,
)
from backend.scheduler.service import scheduler_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Workflow Scheduler"])


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_workflow_or_404(workflow_id: uuid.UUID, user_id: uuid.UUID, db: Session) -> Workflow:
    wf = (
        db.query(Workflow)
        .filter(
            Workflow.id == workflow_id,
            Workflow.user_id == user_id,
            Workflow.deleted_at.is_(None),
        )
        .first()
    )
    if not wf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found.",
        )
    return wf


# ─────────────────────────────────────────────────────────────────────────────
# GET /workflows/scheduled  (must be declared BEFORE /{workflow_id} routes)
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/workflows/scheduled",
    response_model=ScheduledListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all scheduled workflows with next run time",
)
def list_scheduled(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns all workflows that currently have an active APScheduler job.
    Includes the next scheduled run time for each.

    Only shows workflows that belong to the authenticated user.
    """
    if not scheduler_service.is_running:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler is not running.",
        )

    all_scheduled = scheduler_service.list_scheduled(db)

    # Filter to only show the current user's workflows
    user_workflow_ids = {
        str(wf.id)
        for wf in db.query(Workflow.id)
        .filter(Workflow.user_id == current_user.id, Workflow.deleted_at.is_(None))
        .all()
    }
    user_scheduled = [s for s in all_scheduled if str(s.workflow_id) in user_workflow_ids]

    return ScheduledListResponse(total=len(user_scheduled), jobs=user_scheduled)


# ─────────────────────────────────────────────────────────────────────────────
# POST /workflows/{workflow_id}/schedule
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/workflows/{workflow_id}/schedule",
    response_model=ScheduleResponse,
    status_code=status.HTTP_200_OK,
    summary="Create or update a workflow schedule",
)
def schedule_workflow(
    workflow_id: uuid.UUID,
    # Discriminated union: FastAPI picks the right model based on trigger_type
    request: Union[CronSchedule, IntervalSchedule, OnceSchedule],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Set or replace the schedule for a workflow.

    Three schedule types:

    **cron** — standard 5-field cron expression:
    ```json
    { "trigger_type": "cron", "cron": "0 9 * * 1", "timezone": "Asia/Kolkata" }
    ```

    **interval** — run every N minutes/hours/days:
    ```json
    { "trigger_type": "interval", "every_n_hours": 4 }
    ```

    **date** — run once at a specific datetime:
    ```json
    { "trigger_type": "date", "run_at": "2026-06-15T09:00:00Z" }
    ```

    If a schedule already exists, it is replaced. The workflow's `cron_expression`
    field is updated in the database and the APScheduler job store is updated —
    so the new schedule persists across server restarts.
    """
    if not scheduler_service.is_running:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler is not running. Contact an administrator.",
        )

    workflow = _get_workflow_or_404(workflow_id, current_user.id, db)

    try:
        response = scheduler_service.schedule_workflow(workflow, request, db)
        return response
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"[API] Failed to schedule workflow {workflow_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create schedule: {e}",
        )


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /workflows/{workflow_id}/schedule
# ─────────────────────────────────────────────────────────────────────────────

@router.delete(
    "/workflows/{workflow_id}/schedule",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a workflow's schedule",
)
def unschedule_workflow(
    workflow_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Removes the scheduled job for a workflow.
    The workflow itself is NOT deleted — only its scheduling is cleared.
    Idempotent: returns 204 even if no schedule existed.
    """
    workflow = _get_workflow_or_404(workflow_id, current_user.id, db)

    try:
        scheduler_service.unschedule_workflow(workflow, db)
    except Exception as e:
        logger.error(f"[API] Failed to unschedule workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove schedule: {e}",
        )


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /workflows/{workflow_id}/schedule/pause
# ─────────────────────────────────────────────────────────────────────────────

@router.patch(
    "/workflows/{workflow_id}/schedule/pause",
    status_code=status.HTTP_200_OK,
    summary="Pause a scheduled workflow (job remains registered, just won't fire)",
)
def pause_schedule(
    workflow_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Pauses the APScheduler job without removing it.
    Use DELETE to permanently remove. Use this for temporary suspension.
    """
    _get_workflow_or_404(workflow_id, current_user.id, db)
    scheduler_service.pause_workflow(workflow_id)
    return {"message": f"Schedule paused for workflow {workflow_id}."}


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /workflows/{workflow_id}/schedule/resume
# ─────────────────────────────────────────────────────────────────────────────

@router.patch(
    "/workflows/{workflow_id}/schedule/resume",
    status_code=status.HTTP_200_OK,
    summary="Resume a paused workflow schedule",
)
def resume_schedule(
    workflow_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Resumes a previously paused APScheduler job."""
    _get_workflow_or_404(workflow_id, current_user.id, db)
    scheduler_service.resume_workflow(workflow_id)
    return {"message": f"Schedule resumed for workflow {workflow_id}."}


# ─────────────────────────────────────────────────────────────────────────────
# GET /workflows/{workflow_id}/next-run
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/workflows/{workflow_id}/next-run",
    status_code=status.HTTP_200_OK,
    summary="Get the next scheduled run time for a specific workflow",
)
def get_next_run(
    workflow_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the exact datetime of the next scheduled execution,
    or null if the workflow is not currently scheduled.
    """
    _get_workflow_or_404(workflow_id, current_user.id, db)
    next_run = scheduler_service.get_next_run_time(workflow_id)
    return {
        "workflow_id": workflow_id,
        "next_run_time": next_run.isoformat() if next_run else None,
        "is_scheduled": next_run is not None,
    }
