"""
AutoFlow AI X — Workflow Execution Router
==========================================
POST /workflows/{workflow_id}/run                          → Trigger a manual run
GET  /workflows/{workflow_id}/runs                         → List all run history
GET  /workflows/{workflow_id}/runs/{run_id}                → Get run detail with step logs
GET  /workflows/node-types                                 → Get NodeRegistry as JSON (Sprint 2)
POST /workflows/{workflow_id}/nodes/{node_id}/execute      → Execute single node in isolation (Sprint 2)
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
    NodeExecuteRequest,
    NodeExecuteResponse,
    NodeMetadataDTO,
    NodeTypesResponse,
    RunDetail,
    RunListResponse,
    RunSummary,
    StepLogSummary,
    TriggerRunRequest,
    TriggerRunResponse,
)
from backend.workflow.validator.validator import WorkflowValidator

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
    user_id: uuid.UUID,
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
        user_id=user_id,
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

    # ── Pre-run validation gate ───────────────────────────────────────────────
    validator = WorkflowValidator(db=db)
    validation_result = await validator.validate(
        dsl=dsl,
        user_id=current_user.id,
        workflow_id=workflow_id,
    )
    if not validation_result.is_valid:
        error_count = len(validation_result.errors)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": f"Workflow failed validation with {error_count} error(s). Fix them before running.",
                **validation_result.to_response(),
            },
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
        user_id=current_user.id,
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


# ─────────────────────────────────────────────────────────────────────────────
# SPRINT 2: GET /workflows/node-types
# ─────────────────────────────────────────────────────────────────────────────
# IMPORTANT: /node-types must be defined BEFORE /{workflow_id}/... routes
# to avoid FastAPI treating 'node-types' as a workflow_id path parameter.
# It is placed at the END of this file but declared on the same router prefix
# so FastAPI evaluates it after specific paths but before the catch-all.
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/node-types",
    response_model=NodeTypesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get all registered node types (NodeRegistry) as safe DTOs",
    description=(
        "Returns NodeMetadataDTO objects — never serializes NodePlugin directly "
        "(which holds non-serializable callables). Frontend caches this for the session."
    ),
)
def get_node_types(
    current_user: User = Depends(get_current_user),
):
    """
    Returns all NodeRegistry plugins as NodeMetadataDTO objects.
    Safe to send to the client: no executors, no validators, no callable fields.
    Frontend should cache this for the browser session — it’s near-static registry data.
    """
    from backend.workflow.node_registry import NodeRegistry

    plugins = [
        NodeMetadataDTO(
            service=p.service,
            operation=p.operation,
            node_type=p.node_type,
            label=p.label,
            icon=p.icon,
            parameter_schema=p.parameter_schema,
            output_schema=p.output_schema,
            default_params=p.default_params,
            doc_url=p.doc_url,
        )
        for p in NodeRegistry.list_all()
    ]
    return NodeTypesResponse(plugins=plugins, total=len(plugins))


# ─────────────────────────────────────────────────────────────────────────────
# SPRINT 2: POST /workflows/{workflow_id}/nodes/{node_id}/execute
# ─────────────────────────────────────────────────────────────────────────────

# Secret key patterns to scrub from Execute Step output (case-insensitive match).
# Mirrors the guarantee in ExecutionContext.snapshot().
_SECRET_KEY_PATTERNS = frozenset({
    "token", "secret", "password", "passwd", "key", "credential", "auth", "apikey", "api_key",
})


def _scrub_secrets(output: dict) -> dict:
    """
    Remove any top-level output keys whose name contains a secret-looking substring.
    Shallow scrub only — nested keys are not inspected (executors must not nest secrets).
    """
    return {
        k: v for k, v in output.items()
        if not any(pat in k.lower() for pat in _SECRET_KEY_PATTERNS)
    }


def _classify_error(error: str) -> str:
    """
    Map a raw error string to an RFC-002 §3 error boundary type.
    Used so the Inspector can surface appropriate recovery affordances
    (e.g. a Credential Error gets a reconnect prompt, not a 'Continue' option).
    """
    err_lower = error.lower() if error else ""
    if any(w in err_lower for w in ("credential", "token", "auth", "unauthorized", "403", "401")):
        return "credential"
    if any(w in err_lower for w in ("integration", "api", "rate limit", "timeout", "503", "502", "429")):
        return "integration"
    if any(w in err_lower for w in ("schema", "compile", "dsl", "invalid workflow")):
        return "compiler"
    if any(w in err_lower for w in ("validation", "condition_key", "routing_drift", "placeholder")):
        return "validation"
    return "node"


@router.post(
    "/{workflow_id}/nodes/{node_id}/execute",
    response_model=NodeExecuteResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute a single node in isolation (Node Inspector Execute Step)",
)
async def execute_node(
    workflow_id: uuid.UUID,
    node_id: str,
    payload: NodeExecuteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Runs a single DSL node through the real execution pipeline in isolation.
    Returns the real output or real error — no mocked data (RFC-003 §1).

    Uses WorkflowRunner.execute_single_node() (public API — router never
    reaches into private _execute_node()). Same CredentialResolver →
    ExecutionContext → Executor chain as a full run (RFC-002 §1).

    No DB run record is written — this is ephemeral and does not appear
    in run history. The Inspector’s output column caches the result in
    the browser session only.

    Output is scrubbed of secret-looking keys before returning to the client,
    matching the WorkflowContext.snapshot() guarantee from Sprint 1.
    """
    import time

    workflow = _get_workflow_or_404(workflow_id, current_user.id, db)

    # Load and parse DSL
    dsl_json = workflow.ai_context_json
    if not dsl_json:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Workflow has no DSL. Generate it first.",
        )
    try:
        dsl = WorkflowDSL.model_validate(dsl_json)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid workflow DSL: {e}",
        )

    # Find the node by DSL ID
    node = next((n for n in dsl.nodes if n.id == node_id), None)
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node '{node_id}' not found in workflow DSL.",
        )

    # Build an ephemeral runner — no DB run record
    ephemeral_run_id = uuid.uuid4()
    runner = WorkflowRunner(
        dsl=dsl,
        run_id=ephemeral_run_id,
        db=db,
        trigger_payload=payload.trigger_payload,
        user_id=current_user.id,
        workflow_id=workflow_id,
        triggered_by="inspector_execute_step",
    )

    started_at = datetime.now(timezone.utc)
    start_ms = time.monotonic_ns()

    try:
        result = await runner.execute_single_node(
            node=node,
            params_override=payload.params_override,
        )
    except Exception as exc:
        duration_ms = int((time.monotonic_ns() - start_ms) / 1_000_000)
        error_str = str(exc)
        logger.error(
            f"[ExecuteStep] Node '{node_id}' raised exception: {exc}",
            exc_info=True,
        )
        return NodeExecuteResponse(
            node_id=node_id,
            success=False,
            output={},
            error=error_str,
            error_type=_classify_error(error_str),
            duration_ms=duration_ms,
            executed_at=started_at,
        )

    duration_ms = int((time.monotonic_ns() - start_ms) / 1_000_000)

    # Scrub secrets from output before returning to client
    safe_output = _scrub_secrets(result.output or {})

    error_type = _classify_error(result.error) if not result.success and result.error else None

    logger.info(
        f"[ExecuteStep] Node '{node_id}' "
        f"{'succeeded' if result.success else 'failed'} "
        f"in {duration_ms}ms"
    )

    return NodeExecuteResponse(
        node_id=node_id,
        success=result.success,
        output=safe_output,
        error=result.error,
        error_type=error_type,
        duration_ms=duration_ms,
        executed_at=started_at,
    )
