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
