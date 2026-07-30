from sqlalchemy import BigInteger, DateTime
"""
AutoFlow AI X — SQLAlchemy ORM Models
======================================
Mirrors the PostgreSQL schema in backend/database/schema.sql.

Design decisions:
  - All primary keys are UUIDs (server-side generated).
  - Soft deletes on users and workflows via `deleted_at`.
  - JSONB columns use sqlalchemy.dialects.postgresql.JSONB for native Postgres support.
  - All relationships are explicitly declared with back_populates for bidirectionality.
  - Enums are declared as Python Enum classes AND mapped to native PG ENUM types.
  - updated_at is auto-managed by DB triggers; SQLAlchemy also sets it via onupdate.
"""

import enum
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, INET, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy import Enum as SAEnum


# ---------------------------------------------------------------------------
# Base class and helpers
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Python Enum Definitions (mirrored from Postgres ENUM types)
# ---------------------------------------------------------------------------

class UserPlan(str, enum.Enum):
    free = "free"
    starter = "starter"
    pro = "pro"
    enterprise = "enterprise"


class WorkflowStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    paused = "paused"
    archived = "archived"


class RunStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"
    cancelled = "cancelled"
    retrying = "retrying"


class NodeType(str, enum.Enum):
    trigger = "trigger"
    action = "action"
    condition = "condition"
    delay = "delay"
    loop = "loop"
    ai_agent = "ai_agent"
    webhook = "webhook"
    transformer = "transformer"


class IntegrationService(str, enum.Enum):
    gmail = "gmail"
    google_sheets = "google_sheets"
    google_calendar = "google_calendar"
    google_drive = "google_drive"
    whatsapp = "whatsapp"
    slack = "slack"
    notion = "notion"
    hubspot = "hubspot"
    salesforce = "salesforce"
    stripe = "stripe"
    custom_webhook = "custom_webhook"


# ---------------------------------------------------------------------------
# MODEL 1: User
# ---------------------------------------------------------------------------

class User(Base):
    """
    Central identity table.

    Relationships:
      - workflows     → one user has many workflows
      - integrations  → one user has many integrations
      - workflow_runs → one user has many workflow runs
      - api_keys      → one user has many API keys
      - audit_logs    → one user has many audit log entries
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    avatar_url: Mapped[Optional[str]] = mapped_column(Text)
    plan: Mapped[UserPlan] = mapped_column(
        SAEnum(UserPlan, name="user_plan", create_type=False),
        nullable=False,
        default=UserPlan.free,
        index=True,
    )
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Quota tracking
    monthly_run_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_run_reset_at: Mapped[Optional[datetime]] = mapped_column()

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column()

    # Relationships
    workflows: Mapped[List["Workflow"]] = relationship(back_populates="user", lazy="dynamic")
    integrations: Mapped[List["Integration"]] = relationship(back_populates="user", lazy="dynamic")
    workflow_runs: Mapped[List["WorkflowRun"]] = relationship(back_populates="user", lazy="dynamic")
    api_keys: Mapped[List["ApiKey"]] = relationship(back_populates="user", lazy="dynamic")
    audit_logs: Mapped[List["AuditLog"]] = relationship(back_populates="user", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} plan={self.plan}>"


# ---------------------------------------------------------------------------
# MODEL 2: ApiKey
# ---------------------------------------------------------------------------

class ApiKey(Base):
    """
    Personal API keys. Raw key is NEVER stored — only a hash and a short prefix.

    Relationships:
      - user → many API keys belong to one user
    """
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    key_prefix: Mapped[str] = mapped_column(String(12), nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column()
    expires_at: Mapped[Optional[datetime]] = mapped_column()
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)

    # Relationship
    user: Mapped["User"] = relationship(back_populates="api_keys")

    def __repr__(self) -> str:
        return f"<ApiKey id={self.id} prefix={self.key_prefix} user_id={self.user_id}>"


# ---------------------------------------------------------------------------
# MODEL 3: Workflow
# ---------------------------------------------------------------------------

class Workflow(Base):
    """
    Core workflow definition. Owns nodes, edges, and runs.

    Relationships:
      - user           → belongs to one user
      - nodes          → has many workflow_nodes
      - edges          → has many workflow_edges
      - runs           → has many workflow_runs
    """
    __tablename__ = "workflows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[WorkflowStatus] = mapped_column(
        SAEnum(WorkflowStatus, name="workflow_status", create_type=False),
        nullable=False,
        default=WorkflowStatus.draft,
        index=True,
    )

    # AI context
    original_prompt: Mapped[Optional[str]] = mapped_column(Text)
    ai_context_json: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Scheduling
    cron_expression: Mapped[Optional[str]] = mapped_column(String(100))
    timezone: Mapped[str] = mapped_column(String(100), nullable=False, default="UTC")

    # Versioning
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column()

    # Relationships
    user: Mapped["User"] = relationship(back_populates="workflows")
    nodes: Mapped[List["WorkflowNode"]] = relationship(back_populates="workflow", cascade="all, delete-orphan")
    edges: Mapped[List["WorkflowEdge"]] = relationship(back_populates="workflow", cascade="all, delete-orphan")
    runs: Mapped[List["WorkflowRun"]] = relationship(back_populates="workflow", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Workflow id={self.id} name={self.name!r} status={self.status}>"


# ---------------------------------------------------------------------------
# MODEL 4: WorkflowNode
# ---------------------------------------------------------------------------

class WorkflowNode(Base):
    """
    A single step (node) in a workflow — rendered as a box on the canvas.

    config_json holds the node-specific configuration, for example:
      - A Gmail action node: { "to": "{{input.email}}", "subject": "Hello" }
      - A delay node: { "duration_seconds": 3600 }
      - An AI agent node: { "prompt_template": "Summarize: {{input.text}}" }

    Relationships:
      - workflow          → belongs to one workflow
      - outgoing_edges    → edges where this node is the source
      - incoming_edges    → edges where this node is the target
      - step_logs         → run-level execution logs for this node
    """
    __tablename__ = "workflow_nodes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    node_type: Mapped[NodeType] = mapped_column(
        SAEnum(NodeType, name="node_type", create_type=False),
        nullable=False,
        index=True,
    )
    label: Mapped[Optional[str]] = mapped_column(String(255))
    config_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    position_x: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    position_y: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_disabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    workflow: Mapped["Workflow"] = relationship(back_populates="nodes")
    outgoing_edges: Mapped[List["WorkflowEdge"]] = relationship(
        back_populates="source_node",
        foreign_keys="WorkflowEdge.source_node_id",
        cascade="all, delete-orphan",
    )
    incoming_edges: Mapped[List["WorkflowEdge"]] = relationship(
        back_populates="target_node",
        foreign_keys="WorkflowEdge.target_node_id",
        cascade="all, delete-orphan",
    )
    step_logs: Mapped[List["WorkflowRunStepLog"]] = relationship(back_populates="node", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<WorkflowNode id={self.id} type={self.node_type} label={self.label!r}>"


# ---------------------------------------------------------------------------
# MODEL 5: WorkflowEdge
# ---------------------------------------------------------------------------

class WorkflowEdge(Base):
    """
    A directed connection (arrow) between two nodes on the canvas.

    The optional `condition_expr` field allows conditional branching:
    e.g., for a Condition node with two outgoing edges labeled "Yes" and "No",
    each edge carries its own condition expression evaluated at runtime.

    Relationships:
      - workflow      → belongs to one workflow
      - source_node   → the node this edge originates from
      - target_node   → the node this edge points to
    """
    __tablename__ = "workflow_edges"
    __table_args__ = (
        UniqueConstraint("workflow_id", "source_node_id", "target_node_id", "label", name="edges_unique_connection"),
        CheckConstraint("source_node_id != target_node_id", name="edges_no_self_loop"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    source_node_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflow_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    target_node_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflow_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    label: Mapped[Optional[str]] = mapped_column(String(100))
    condition_expr: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)

    # Relationships
    workflow: Mapped["Workflow"] = relationship(back_populates="edges")
    source_node: Mapped["WorkflowNode"] = relationship(
        back_populates="outgoing_edges",
        foreign_keys=[source_node_id],
    )
    target_node: Mapped["WorkflowNode"] = relationship(
        back_populates="incoming_edges",
        foreign_keys=[target_node_id],
    )

    def __repr__(self) -> str:
        return f"<WorkflowEdge {self.source_node_id} → {self.target_node_id} label={self.label!r}>"


# ---------------------------------------------------------------------------
# MODEL 6: WorkflowRun
# ---------------------------------------------------------------------------

class WorkflowRun(Base):
    """
    Records each execution of a workflow. Supports retry chains via parent_run_id.

    Relationships:
      - workflow    → belongs to one workflow
      - user        → belongs to one user
      - step_logs   → has many per-node step log entries
      - parent_run  → self-referential: retry run points to original
      - child_runs  → all retry attempts of this run
    """
    __tablename__ = "workflow_runs"
    __table_args__ = (
        CheckConstraint("attempt_number >= 1", name="runs_attempt_positive"),
        CheckConstraint("finished_at IS NULL OR finished_at >= started_at", name="runs_finished_after_start"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[RunStatus] = mapped_column(
        SAEnum(RunStatus, name="run_status", create_type=False),
        nullable=False,
        default=RunStatus.pending,
        index=True,
    )

    # Trigger context
    trigger_type: Mapped[Optional[str]] = mapped_column(String(50))
    trigger_payload: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Execution context
    context_snapshot: Mapped[Optional[dict]] = mapped_column(JSONB)
    output_json: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Retry tracking
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    parent_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("workflow_runs.id"), nullable=True, index=True
    )

    # Error details
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    error_stack: Mapped[Optional[str]] = mapped_column(Text)

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column()
    finished_at: Mapped[Optional[datetime]] = mapped_column()
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)

    # Relationships
    workflow: Mapped["Workflow"] = relationship(back_populates="runs")
    user: Mapped["User"] = relationship(back_populates="workflow_runs")
    step_logs: Mapped[List["WorkflowRunStepLog"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    parent_run: Mapped[Optional["WorkflowRun"]] = relationship(
        back_populates="child_runs", remote_side="WorkflowRun.id"
    )
    child_runs: Mapped[List["WorkflowRun"]] = relationship(back_populates="parent_run")

    def __repr__(self) -> str:
        return f"<WorkflowRun id={self.id} status={self.status} attempt={self.attempt_number}>"


# ---------------------------------------------------------------------------
# MODEL 7: WorkflowRunStepLog
# ---------------------------------------------------------------------------

class WorkflowRunStepLog(Base):
    """
    Granular per-node execution record for a single workflow run.
    Stores input/output payloads and timing for every step.

    Relationships:
      - run   → belongs to one WorkflowRun
      - node  → belongs to one WorkflowNode
    """
    __tablename__ = "workflow_run_step_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    node_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflow_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[RunStatus] = mapped_column(
        SAEnum(RunStatus, name="run_status", create_type=False),
        nullable=False,
        default=RunStatus.pending,
        index=True,
    )
    input_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    output_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[Optional[datetime]] = mapped_column()
    finished_at: Mapped[Optional[datetime]] = mapped_column()
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)

    # Relationships
    run: Mapped["WorkflowRun"] = relationship(back_populates="step_logs")
    node: Mapped["WorkflowNode"] = relationship(back_populates="step_logs")

    def __repr__(self) -> str:
        return f"<WorkflowRunStepLog run={self.run_id} node={self.node_id} status={self.status}>"


# ---------------------------------------------------------------------------
# MODEL 8: Integration
# ---------------------------------------------------------------------------

class Integration(Base):
    """
    Stores encrypted OAuth tokens / API credentials for third-party services.

    SECURITY NOTE: `credentials_encrypted` must always be set using your
    application-level encryption service (e.g. Fernet / AES-256-GCM).
    Never store raw tokens here.

    Relationships:
      - user → belongs to one user
    """
    __tablename__ = "integrations"
    __table_args__ = (
        UniqueConstraint("user_id", "service_name", "display_name", name="integrations_unique_per_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    service_name: Mapped[IntegrationService] = mapped_column(
        SAEnum(IntegrationService, name="integration_service", create_type=False),
        nullable=False,
        index=True,
    )
    display_name: Mapped[Optional[str]] = mapped_column(String(255))
    credentials_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    scopes: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column()
    last_synced_at: Mapped[Optional[datetime]] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow, nullable=False)

    # Relationship
    user: Mapped["User"] = relationship(back_populates="integrations")

    def __repr__(self) -> str:
        return f"<Integration id={self.id} service={self.service_name} user_id={self.user_id}>"


# ---------------------------------------------------------------------------
# MODEL 9: IndustryTemplate
# ---------------------------------------------------------------------------

class IndustryTemplate(Base):
    """
    Pre-built workflow templates for specific industries.
    Users can browse the template gallery and clone these into their workspace.

    dsl_json contains the full workflow definition:
    {
        "nodes": [...],
        "edges": [...]
    }

    Relationships:
      - created_by → optionally created by a user (null = system template)
    """
    __tablename__ = "industry_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    industry: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text))
    dsl_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(Text)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    use_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow, nullable=False)

    # Relationship (optional)
    creator: Mapped[Optional["User"]] = relationship(foreign_keys=[created_by])

    def __repr__(self) -> str:
        return f"<IndustryTemplate id={self.id} name={self.name!r} industry={self.industry}>"


# ---------------------------------------------------------------------------
# MODEL 10: AuditLog
# ---------------------------------------------------------------------------

class AuditLog(Base):
    """
    Immutable event log. Records every significant user action.
    Uses BIGSERIAL (int) PK for high-volume append performance.

    action examples:
      'workflow.created', 'workflow.deleted', 'run.triggered',
      'integration.connected', 'integration.deleted', 'user.plan_upgraded'

    Relationships:
      - user → belongs to a user (nullable for system events)
    """
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[Optional[str]] = mapped_column(String(100))
    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    event_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSONB)
    ip_address: Mapped[Optional[str]] = mapped_column(INET)
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False, index=True)

    # Relationship
    user: Mapped[Optional["User"]] = relationship(back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action} user_id={self.user_id}>"


# MODEL 8: ExecutionEvent
class ExecutionEvent(Base):
    __tablename__ = "execution_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True, autoincrement=True)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    node_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True) # e.g. RUN_STARTED, NODE_STARTED, NODE_COMPLETED, RUN_SUSPENDED
    payload: Mapped[dict] = mapped_column(JSONB, nullable=True) # Details like state snapshots, errors, output
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<ExecutionEvent id={self.id} run_id={self.run_id} type={self.event_type}>"
