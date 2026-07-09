"""
AutoFlow AI X — Workflow Planner Router
POST /ai/plan-workflow   — generate a full new workflow DSL
POST /ai/add-step        — add node(s) to an existing workflow (returns delta only)
GET  /ai/capabilities    — list all registered capability patterns
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.database.models import User
from backend.database.session import get_db
from backend.workflow.capability_registry import CapabilityRegistry
from backend.workflow.planner import service, editor_service
from backend.workflow.planner.schemas import (
    AddStepRequest,
    AddStepResponse,
    CapabilitiesListResponse,
    CapabilityPatternDTO,
    PlanWorkflowRequest,
    PlanWorkflowResponse,
)

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
            existing_dsl=payload.existing_dsl,
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


@router.post(
    "/add-step",
    response_model=AddStepResponse,
    status_code=status.HTTP_200_OK,
    summary="Add node(s) to an existing workflow (returns delta only, RFC-001 §1)",
)
async def add_step(
    payload: AddStepRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Add one or more nodes to an existing workflow using AI + the Capability Registry.

    Response contract:
      - Returns ONLY a DSL delta (new_nodes, new_edges, removed_edges).
      - Never returns a reconstructed full graph.
      - The frontend WorkflowMutationService.addStep() is the sole component
        responsible for merging the delta into the canonical DSL.
      - Registry-driven expansion is used when a Capability pattern matches
        (confidence >= 0.40); otherwise the LLM selects a plugin and NodeRegistry
        provides the default params.
    """
    try:
        return await editor_service.add_step(
            current_dsl=payload.current_dsl,
            user_intent=payload.user_intent,
            insert_after_node_id=payload.insert_after_node_id,
            workflow_id=payload.workflow_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI service temporarily unavailable. Please try again. ({e})",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}",
        )


@router.get(
    "/capabilities",
    response_model=CapabilitiesListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all registered Capability Registry patterns (RFC-001 §4)",
)
async def list_capabilities(
    current_user: User = Depends(get_current_user),
):
    """
    Returns all registered multi-node capability patterns from the Capability Registry.

    The Capability Registry is the backend source of truth — patterns are never
    duplicated on the frontend. The frontend fetches this list once per session
    to populate the AddStepPanel's capability chips.
    """
    patterns = CapabilityRegistry.list_all()
    dtos = [
        CapabilityPatternDTO(
            name=p.name,
            description=p.description,
            keywords=p.keywords,
            node_keys=p.nodes,
            explanation=p.explanation,
            tags=p.tags,
            node_count=len(p.nodes),
        )
        for p in patterns
    ]
    return CapabilitiesListResponse(patterns=dtos, total=len(dtos))
