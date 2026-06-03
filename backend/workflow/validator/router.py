"""
AutoFlow AI X — Validator API Router
======================================
POST /workflows/validate — validate a DSL before saving or executing
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.database.models import User
from backend.database.session import get_db
from backend.workflow.dsl.schema import WorkflowDSL
from backend.workflow.validator.schemas import (
    ValidateWorkflowRequest,
    ValidateWorkflowResponse,
    ValidationIssueOut,
)
from backend.workflow.validator.validator import WorkflowValidator

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Workflow Validation"])


@router.post(
    "/workflows/validate",
    response_model=ValidateWorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate a workflow DSL before saving or running",
)
async def validate_workflow(
    payload: ValidateWorkflowRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Runs all 5 validation checks against a workflow DSL:

    1. **Schema** — required params, field types, cron format
    2. **Graph**  — reachability from trigger, no circular paths
    3. **Credentials** — user has connected required integrations
    4. **Templates** — all `{{variable}}` references exist and are reachable
    5. **Schedule** — no cron conflict with other user workflows

    **Returns:**
    - `valid: true` + any `warnings` if all checks pass
    - `valid: false` + `errors` list if any check fails

    Each error/warning includes:
    - `code` — machine-readable error code (e.g. `MISSING_CREDENTIAL`)
    - `node_id` — which node caused the issue (for canvas highlighting)
    - `message` — human-readable explanation
    - `detail` — extra context (connect URLs, available nodes, etc.)

    **Frontend usage:**
    Use `node_id` to apply a red border on that node in the canvas.
    Show `message` in a tooltip on hover.
    """
    # 1. Parse DSL (catches structural Pydantic errors)
    try:
        dsl = WorkflowDSL.model_validate(payload.dsl)
    except PydanticValidationError as e:
        # Surface Pydantic errors as structured validation errors
        errors = []
        for err in e.errors():
            loc = " → ".join(str(x) for x in err["loc"])
            errors.append(
                ValidationIssueOut(
                    code="INVALID_DSL_SCHEMA",
                    message=f"{loc}: {err['msg']}",
                    severity="error",
                    node_id=_extract_node_id_from_pydantic_loc(err["loc"]),
                )
            )
        return ValidateWorkflowResponse(
            valid=False,
            errors=errors,
            warnings=[],
            summary=f"DSL schema is invalid: {len(errors)} error(s).",
        )

    # 2. Run all validation checks
    validator = WorkflowValidator(db=db)
    result = await validator.validate(
        dsl=dsl,
        user_id=current_user.id,
        workflow_id=payload.workflow_id,
    )

    # 3. Build response
    error_count = len(result.errors)
    warning_count = len(result.warnings)

    if result.is_valid:
        summary = f"Workflow is valid. {warning_count} advisory warning(s)." if warning_count else "Workflow is valid."
    else:
        summary = (
            f"Workflow has {error_count} error(s) and {warning_count} warning(s). "
            f"Fix errors before running."
        )

    return ValidateWorkflowResponse(
        valid=result.is_valid,
        errors=[ValidationIssueOut(**e.to_dict()) for e in result.errors],
        warnings=[ValidationIssueOut(**w.to_dict()) for w in result.warnings],
        summary=summary,
    )


def _extract_node_id_from_pydantic_loc(loc: tuple) -> str | None:
    """
    Try to extract a node ID from a Pydantic validation error location.
    E.g. ("nodes", 2, "params", "to") → look up the node at index 2.
    """
    # If loc is like ("nodes", <int>, ...) we can find the node index
    if len(loc) >= 2 and loc[0] == "nodes" and isinstance(loc[1], int):
        return f"nodes[{loc[1]}]"  # Frontend can use this to highlight by index
    return None
