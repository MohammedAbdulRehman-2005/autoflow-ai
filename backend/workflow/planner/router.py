"""
AutoFlow AI X — Workflow Planner Router
POST /ai/plan-workflow
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.database.models import User
from backend.database.session import get_db
from backend.workflow.planner import service
from backend.workflow.planner.schemas import PlanWorkflowRequest, PlanWorkflowResponse

router = APIRouter(prefix="/ai", tags=["AI Workflow Planner"])


@router.post(
    "/plan-workflow",
    response_model=PlanWorkflowResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a workflow from natural language intent using AI",
)
async def plan_workflow(
    payload: PlanWorkflowRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Converts a structured intent (goal, trigger, integrations, industry) into a
    fully validated, executable AutoFlow workflow DSL using the Groq LLM.

    The pipeline:
    1. Builds a context-rich prompt with the full DSL specification
    2. Calls Groq (llama-3.3-70b-versatile) to generate the DSL
    3. Validates the JSON structure with Pydantic
    4. Validates the graph semantics (cycles, reachability, condition integrity)
    5. Retries with error feedback if validation fails (up to 2 extra attempts)
    6. Saves the validated workflow to the database
    7. Returns the workflow ID, DSL, and graph statistics

    **Requires:** Bearer token authentication
    """
    try:
        return await service.plan_workflow(
            workflow_name=payload.workflow_name,
            intent=payload.intent,
            user_id=current_user.id,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except RuntimeError as e:
        # Groq API failure
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI service temporarily unavailable. Please try again. ({e})",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}",
        )
