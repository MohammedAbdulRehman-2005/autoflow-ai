"""
AutoFlow AI X — Engine API Schemas
=====================================
Request/response models for workflow execution endpoints.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Request ───────────────────────────────────────────────────────────────────

class TriggerRunRequest(BaseModel):
    """Body for POST /workflows/:id/run — manually trigger a workflow."""
    trigger_payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Input data injected into the trigger context ({{trigger.payload.*}})",
    )
    notes: Optional[str] = Field(
        None,
        description="Optional human note about why this run was triggered manually",
    )


# ── Response ──────────────────────────────────────────────────────────────────

class StepLogSummary(BaseModel):
    id: uuid.UUID
    node_id: uuid.UUID
    status: str
    duration_ms: Optional[int]
    error_message: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]

    model_config = {"from_attributes": True}


class RunDetail(BaseModel):
    """Full detail of a single workflow run, including per-node step logs."""
    id: uuid.UUID
    workflow_id: uuid.UUID
    status: str
    trigger_type: Optional[str]
    trigger_payload: Optional[Dict[str, Any]]
    attempt_number: int
    max_attempts: int
    error_message: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    duration_ms: Optional[int]
    created_at: datetime
    step_logs: List[StepLogSummary] = []

    model_config = {"from_attributes": True}


class RunSummary(BaseModel):
    """Compact run info for the list endpoint."""
    id: uuid.UUID
    status: str
    trigger_type: Optional[str]
    attempt_number: int
    error_message: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    duration_ms: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


class TriggerRunResponse(BaseModel):
    run_id: uuid.UUID
    workflow_id: uuid.UUID
    status: str
    message: str


class RunListResponse(BaseModel):
    workflow_id: uuid.UUID
    total: int
    runs: List[RunSummary]
