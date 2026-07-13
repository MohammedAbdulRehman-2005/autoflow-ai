"""
AutoFlow AI X — API schemas for the Workflow Planner endpoint.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# REQUEST
# ─────────────────────────────────────────────────────────────────────────────

class IntentDetails(BaseModel):
    """
    Structured intent extracted from the user's natural language input
    (after the follow-up question engine has collected all required info).
    """
    goal: str = Field(
        ...,
        description="The business objective, e.g. 'Send appointment reminders to patients'",
    )
    trigger: str = Field(
        ...,
        description="When/how to trigger the workflow, e.g. 'every day at 9 AM' or 'when a form is submitted'",
    )
    industry: Optional[str] = Field(
        None,
        description="Industry context for better template selection, e.g. 'healthcare', 'real_estate'",
    )
    integrations: List[str] = Field(
        default_factory=list,
        description="List of services to integrate, e.g. ['google_sheets', 'gmail', 'slack']",
    )
    extra_details: Optional[Dict[str, Any]] = Field(
        None,
        description="Any additional context the user provided (sheet IDs, email templates, etc.)",
    )


class PlanWorkflowRequest(BaseModel):
    workflow_name: str = Field(..., min_length=1, max_length=255)
    intent: IntentDetails
    existing_dsl: Optional[Dict[str, Any]] = Field(
        None,
        description="The current WorkflowDSL JSON when iteratively modifying an existing workflow."
    )
    # user_id injected from auth token in the router — not provided by client


# ─────────────────────────────────────────────────────────────────────────────
# RESPONSE
# ─────────────────────────────────────────────────────────────────────────────

class GraphStats(BaseModel):
    node_count: int
    edge_count: int
    trigger_type: str
    services_used: List[str]
    has_condition: bool
    has_loop: bool
    has_ai_agent: bool


class PlanWorkflowResponse(BaseModel):
    workflow_id: uuid.UUID
    workflow_name: str
    dsl: Dict[str, Any]
    graph_stats: GraphStats
    validation_warnings: List[str]
    groq_attempts: int           # How many LLM calls were needed (1 = perfect first try)
    created_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# SPRINT 3 — ADD STEP REQUEST / RESPONSE (RFC-001 §1, §4)
# ─────────────────────────────────────────────────────────────────────────────

class AddStepRequest(BaseModel):
    """
    Request to add one or more nodes to an existing workflow using AI +
    the Capability Registry (RFC-001 §4).

    The backend returns ONLY a delta — the frontend mutationService.addStep()
    is the sole component responsible for applying the delta to the canonical DSL.
    """
    current_dsl: Dict[str, Any] = Field(
        ...,
        description="The complete current WorkflowDSL JSON.",
    )
    user_intent: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Free-text description of the desired next step.",
    )
    insert_after_node_id: Optional[str] = Field(
        None,
        description="Insert after this node ID, splicing any existing outgoing edge. "
                    "Null means append after the last node.",
    )
    workflow_id: Optional[uuid.UUID] = None


class CapabilityMatchDTO(BaseModel):
    """Serialisable CapabilityMatch for the API response (includes confidence + keywords)."""
    capability_name: str
    description: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    matched_keywords: List[str]
    explanation: str
    tags: List[str] = Field(default_factory=list)
    node_count: int


class EdgePairDTO(BaseModel):
    """A (source_id, target_id) pair identifying a specific DSL edge to remove."""
    source_id: str
    target_id: str


class DeltaResult(BaseModel):
    """
    The DSL delta returned by the add-step endpoint.

    Backend returns ONLY the delta — never a reconstructed full graph.
    The frontend mutationService.addStep() merges this into the current DSL.
    """
    new_nodes: List[Dict[str, Any]] = Field(default_factory=list)
    new_edges: List[Dict[str, Any]] = Field(default_factory=list)
    removed_edges: List[EdgePairDTO] = Field(default_factory=list)


class AddStepResponse(BaseModel):
    """Response from POST /ai/add-step."""
    delta: DeltaResult
    explanation: str = Field(..., description="'Why this change?' for the DiffPreview UI.")
    capability_match: Optional[CapabilityMatchDTO] = Field(
        None,
        description="Set when a Capability Registry pattern was used; null for LLM-chosen single nodes.",
    )
    applied_node_ids: List[str] = Field(default_factory=list)
    registry_driven: bool = Field(
        True,
        description="True when nodes came from NodeRegistry defaults; False when LLM generated params.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# CAPABILITIES LIST (GET /ai/capabilities)
# ─────────────────────────────────────────────────────────────────────────────

class CapabilityPatternDTO(BaseModel):
    """Serialisable CapabilityPattern for the capabilities list endpoint."""
    name: str
    description: str
    keywords: List[str]
    node_keys: List[str]
    explanation: str
    tags: List[str]
    node_count: int


class CapabilitiesListResponse(BaseModel):
    patterns: List[CapabilityPatternDTO]
    total: int
