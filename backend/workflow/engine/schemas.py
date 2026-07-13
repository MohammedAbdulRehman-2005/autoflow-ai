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


# ─────────────────────────────────────────────────────────────────────────────
# SPRINT 2 — Node Inspector Execute Step + Node Types endpoint
# ─────────────────────────────────────────────────────────────────────────────

class NodeExecuteRequest(BaseModel):
    """
    Request body for POST /workflows/{workflow_id}/nodes/{node_id}/execute
    
    params_override: merged on top of the node's stored params for this
    one-shot run only. Never persisted. The Inspector always reads latest
    locally-patched params, so the frontend sends them here at click time.
    """
    node_id: str = Field(..., description="DSL node ID to execute.")
    params_override: Dict[str, Any] = Field(
        default_factory=dict,
        description="Param overrides merged over stored node.params for this run only.",
    )
    trigger_payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional trigger context injected into ExecutionContext.",
    )


class NodeExecuteResponse(BaseModel):
    """
    Response from POST /workflows/{workflow_id}/nodes/{node_id}/execute

    SECRET EXCLUSION GUARANTEE—matches WorkflowContext.snapshot() contract:
    - output is scrubbed of any key whose name contains 'token', 'secret',
      'password', 'key', 'credential', or 'auth' (case-insensitive).
    - This is enforced in WorkflowRunner.execute_single_node(), not assumed.
    - error_type classifies the failure layer (RFC-002 §3 Error Boundaries)
      so the Inspector can surface appropriate recovery affordances.

    execute_once and always_output_data are no-ops in this context:
    they only apply to full workflow runs with a real run_id.
    """
    node_id: str
    success: bool
    output: Dict[str, Any]     # Scrubbed — no secrets
    error: Optional[str] = None
    error_type: Optional[str] = Field(
        None,
        description="'node' | 'integration' | 'credential' | 'compiler' | 'validation'",
    )
    duration_ms: int
    executed_at: datetime
    # Sprint 3.5 — execution telemetry (metadata only; no behavior change)
    retry_count: int = Field(0, description="Number of retry attempts made (0 = succeeded on first attempt).")
    credential_used: Optional[str] = Field(None, description="Credential ID used for this execution (scrubbed of value).")
    cache_hit: bool = Field(False, description="True if result was served from cache (future capability).")
    # AI-specific telemetry (populated only for AI/LLM nodes)
    llm_tokens: Optional[int] = Field(None, description="Total tokens consumed by LLM (prompt + completion).")
    estimated_cost: Optional[float] = Field(None, description="Estimated API cost in USD (informational).")
    provider: Optional[str] = Field(None, description="AI provider name e.g. 'groq', 'openai'.")
    model_used: Optional[str] = Field(None, description="Model identifier used for this execution.")


# ── Node Types ─────────────────────────────────────────────────────────────────────────

class NodeMetadataDTO(BaseModel):
    """
    Safe serialization of a NodePlugin for the /workflows/node-types endpoint.

    NEVER serialize NodePlugin directly: it contains non-serializable callables
    (executor_class, validator) and would leak implementation internals to the client.
    This DTO exposes only what the Inspector UI and the parameter form generator need.
    """
    service: str
    operation: str
    node_type: str
    label: str
    icon: str
    parameter_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    default_params: Dict[str, Any]
    doc_url: Optional[str] = None

    # Sprint 3.5 extended metadata
    display_name: Optional[str] = None
    category: str = "general"
    tags: List[str] = []
    recommended_after: List[str] = []
    supports_streaming: bool = False
    supports_preview: bool = False
    supports_retry: bool = True
    supports_batch: bool = False
    estimated_latency: str = "medium"
    required_scopes: List[str] = []


class NodeTypesResponse(BaseModel):
    """Response from GET /workflows/node-types."""
    plugins: List[NodeMetadataDTO]
    total: int
