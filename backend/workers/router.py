"""
AutoFlow AI X — Run Status Polling Router
==========================================
GET /api/v1/runs/{run_id}/status  — poll Celery task + DB status
GET /api/v1/runs/{run_id}         — full run detail
"""

import logging
import uuid
from typing import Any, Dict, Optional

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.database.models import RunStatus, User, WorkflowRun
from backend.database.session import get_db
from backend.workers.celery_app import celery_app

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/runs", tags=["Runs"])


class RunStatusResponse(BaseModel):
    run_id:          str
    workflow_id:     str
    status:          str
    celery_task_id:  Optional[str]
    celery_state:    Optional[str]
    attempt_number:  int
    duration_ms:     Optional[int]
    started_at:      Optional[str]
    finished_at:     Optional[str]
    error_message:   Optional[str]
    runtime:         Optional[str]   # "langgraph" | "simple"
    context_data:    Optional[Dict[str, Any]]


@router.get("/{run_id}/status", response_model=RunStatusResponse)
async def get_run_status(
    run_id:       str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """
    Lightweight polling endpoint.
    Frontend polls this every 2-3 seconds until status is terminal.
    """
    try:
        _run_id = uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run_id format.")

    run: WorkflowRun = db.query(WorkflowRun).filter(WorkflowRun.id == _run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found.")

    if run.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    # Query Celery live state
    celery_state = None
    if run.celery_task_id:
        try:
            result      = AsyncResult(run.celery_task_id, app=celery_app)
            celery_state = result.state
        except Exception as e:
            logger.warning(f"Celery state query failed for task {run.celery_task_id}: {e}")

    return RunStatusResponse(
        run_id         = str(run.id),
        workflow_id    = str(run.workflow_id),
        status         = run.status,
        celery_task_id = run.celery_task_id,
        celery_state   = celery_state,
        attempt_number = run.attempt_number,
        duration_ms    = run.duration_ms,
        started_at     = run.started_at.isoformat() if run.started_at else None,
        finished_at    = run.finished_at.isoformat() if run.finished_at else None,
        error_message  = run.error_message,
        runtime        = run.context_snapshot.get("runtime") if run.context_snapshot else None,
        context_data   = None,
    )


@router.get("/{run_id}", response_model=RunStatusResponse)
async def get_run_detail(
    run_id:       str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """Full run detail including context_data (output of all nodes)."""
    try:
        _run_id = uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run_id format.")

    run = db.query(WorkflowRun).filter(WorkflowRun.id == _run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found.")
    if run.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    celery_state = None
    if run.celery_task_id:
        try:
            result = AsyncResult(run.celery_task_id, app=celery_app)
            celery_state = result.state
        except Exception: pass

    snapshot = run.context_snapshot or {}
    return RunStatusResponse(
        run_id         = str(run.id),
        workflow_id    = str(run.workflow_id),
        status         = run.status,
        celery_task_id = run.celery_task_id,
        celery_state   = celery_state,
        attempt_number = run.attempt_number,
        duration_ms    = run.duration_ms,
        started_at     = run.started_at.isoformat() if run.started_at else None,
        finished_at    = run.finished_at.isoformat() if run.finished_at else None,
        error_message  = run.error_message,
        runtime        = snapshot.get("runtime"),
        context_data   = snapshot.get("node_outputs"),
    )
