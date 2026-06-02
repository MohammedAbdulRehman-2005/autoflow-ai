"""
AutoFlow AI X — Workflow Execution Router
==========================================
POST /workflows/{workflow_id}/run  → Trigger a manual run
GET  /workflows/{workflow_id}/runs → List all run history
GET  /workflows/{workflow_id}/runs/{run_id} → Get run detail with step logs
"""

import asyncio
import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.database.models import (
    RunStatus,
    Workflow,
    WorkflowRun,
    WorkflowRunStepLog,
)
from backend.database.session import get_db
from backend.database.models import User
from backend.workflow.dsl.schema import WorkflowDSL
from backend.workflow.engine.runner import WorkflowRunner
from backend.workflow.engine.schemas import (
    RunDetail,
    RunListResponse,
    RunSummary,
    StepLogSummary,
    TriggerRunRequest,
    TriggerRunResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workflows", tags=["Workflow Execution"])


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def _get_workflow_or_404(workflow_id: uuid.UUID, user_id: uuid.UUID, db: Session) -> Workflow:
    """Load a workflow, ensuring it belongs to the current user."""
    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.user_id == user_id, Workflow.deleted_at.is_(None))
        .first()
    )
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found.",
        )
    return workflow


async def _run_workflow_background(
    run_id: uuid.UUID,
    dsl: WorkflowDSL,
    trigger_payload: dict,
    db: Session,
) -> None:
    """
    Background task: instantiate the runner and execute the workflow.
    Any exception is caught and written to the run record by the runner itself.
    """
    runner = WorkflowRunner(
        dsl=dsl,
        run_id=run_id,
        db=db,
        trigger_payload=trigger_payload,
    )
    try:
        await runner.run()
    except Exception as e:
        logger.error(f"[Engine] Background run {run_id} failed: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# POST /workflows/{workflow_id}/run
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/{workflow_id}/run",
    response_model=TriggerRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Manually trigger a workflow run",
)
async def trigger_run(
    workflow_id: uuid.UUID,
    payload: TriggerRunRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Triggers an immediate manual execution of a workflow.

    The run starts in the background — the endpoint returns immediately with
    the `run_id` so the client can poll `/runs/{run_id}` for status.

    - Validates the workflow exists and belongs to the user
    - Loads the DSL from the database
    - Creates a `workflow_runs` record with status=pending
    - Fires the execution engine in the background
    - Returns `202 Accepted` with the run_id
    """
    workflow = _get_workflow_or_404(workflow_id, current_user.id, db)

    # Load and validate DSL
    dsl_json = workflow.ai_context_json
    if not dsl_json:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Workflow has no DSL defined. Generate it first using the planner.",
        )
    try:
        dsl = WorkflowDSL.model_validate(dsl_json)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid workflow DSL in database: {e}",
        )

    # Create the run record
    run_id = uuid.uuid4()
    run = WorkflowRun(
        id=run_id,
        workflow_id=workflow.id,
        user_id=current_user.id,
        status=RunStatus.pending.value,
        trigger_type="manual",
        trigger_payload=payload.trigger_payload,
        attempt_number=1,
        max_attempts=3,
    )
    db.add(run)
    db.commit()

    # Fire execution in background
    background_tasks.add_task(
        _run_workflow_background,
        run_id=run_id,
        dsl=dsl,
        trigger_payload=payload.trigger_payload,
        db=db,
    )

    logger.info(
        f"[API] Manual run {run_id} queued for workflow '{workflow.name}' "
        f"by user {current_user.id}"
    )

    return TriggerRunResponse(
        run_id=run_id,
        workflow_id=workflow.id,
        status="pending",
        message=f"Workflow run started. Poll GET /workflows/{workflow_id}/runs/{run_id} for status.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /workflows/{workflow_id}/runs
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{workflow_id}/runs",
    response_model=RunListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all run history for a workflow",
)
def list_runs(
    workflow_id: uuid.UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: str = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns paginated run history for a workflow, newest first.

    Optional query params:
      - `status`: filter by run status (pending|running|success|failed|cancelled|retrying)
      - `limit`: page size (default 20, max 100)
      - `offset`: pagination offset
    """
    _get_workflow_or_404(workflow_id, current_user.id, db)

    query = db.query(WorkflowRun).filter(WorkflowRun.workflow_id == workflow_id)
    if status_filter:
        query = query.filter(WorkflowRun.status == status_filter)

    total = query.count()
    runs = (
        query.order_by(WorkflowRun.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return RunListResponse(
        workflow_id=workflow_id,
        total=total,
        runs=[RunSummary.model_validate(r) for r in runs],
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /workflows/{workflow_id}/runs/{run_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{workflow_id}/runs/{run_id}",
    response_model=RunDetail,
    status_code=status.HTTP_200_OK,
    summary="Get full detail of a single run including per-node step logs",
)
def get_run(
    workflow_id: uuid.UUID,
    run_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns full run detail including every node's input/output/error/timing.
    This is the data source for the monitoring dashboard.
    """
    _get_workflow_or_404(workflow_id, current_user.id, db)

    run = (
        db.query(WorkflowRun)
        .filter(WorkflowRun.id == run_id, WorkflowRun.workflow_id == workflow_id)
        .first()
    )
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found.",
        )

    step_logs = (
        db.query(WorkflowRunStepLog)
        .filter(WorkflowRunStepLog.run_id == run_id)
        .order_by(WorkflowRunStepLog.started_at)
        .all()
    )

    run_detail = RunDetail.model_validate(run)
    run_detail.step_logs = [StepLogSummary.model_validate(s) for s in step_logs]

    return run_detail
