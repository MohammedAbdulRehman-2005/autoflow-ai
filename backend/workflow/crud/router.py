import uuid
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from backend.auth.dependencies import get_current_user
from backend.database.models import User, Workflow, WorkflowStatus
from backend.database.session import get_db

router = APIRouter(prefix="/workflows", tags=["Workflows"])

# ─────────────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────────────

class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    dsl_json: dict = Field(..., description="The WorkflowDSL representation")

class WorkflowUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None
    dsl_json: Optional[dict] = None

class WorkflowResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    dsl_json: Optional[dict] = Field(None, alias="ai_context_json")

    model_config = {"from_attributes": True, "populate_by_name": True}

class WorkflowListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[WorkflowResponse]

# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("", response_model=WorkflowListResponse)
def list_workflows(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Workflow).filter(
        Workflow.user_id == current_user.id,
        Workflow.deleted_at.is_(None)
    )
    if status_filter:
        query = query.filter(Workflow.status == status_filter)
        
    total = query.count()
    items = query.order_by(Workflow.updated_at.desc()).offset(offset).limit(limit).all()
    
    return WorkflowListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=items
    )

@router.get("/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(
    workflow_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workflow = db.query(Workflow).filter(
        Workflow.id == workflow_id,
        Workflow.user_id == current_user.id,
        Workflow.deleted_at.is_(None)
    ).first()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
        
    return workflow

@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
def create_workflow(
    payload: WorkflowCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workflow = Workflow(
        user_id=current_user.id,
        name=payload.name,
        description=payload.description,
        status=WorkflowStatus.draft,
        ai_context_json=payload.dsl_json,
        version=1
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow

@router.patch("/{workflow_id}", response_model=WorkflowResponse)
def update_workflow(
    workflow_id: uuid.UUID,
    payload: WorkflowUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workflow = db.query(Workflow).filter(
        Workflow.id == workflow_id,
        Workflow.user_id == current_user.id,
        Workflow.deleted_at.is_(None)
    ).first()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
        
    if payload.name is not None:
        workflow.name = payload.name
    if payload.description is not None:
        workflow.description = payload.description
    if payload.status is not None:
        workflow.status = payload.status
    if payload.dsl_json is not None:
        workflow.ai_context_json = payload.dsl_json
        workflow.version += 1
        
    db.commit()
    db.refresh(workflow)
    return workflow

@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow(
    workflow_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workflow = db.query(Workflow).filter(
        Workflow.id == workflow_id,
        Workflow.user_id == current_user.id,
        Workflow.deleted_at.is_(None)
    ).first()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
        
    workflow.deleted_at = datetime.utcnow()
    db.commit()
    return None
