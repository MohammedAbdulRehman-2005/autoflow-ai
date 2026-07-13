"""
AutoFlow AI X â€” Node Registry  (RFC-001 Â§3)
=============================================
Promotes the executor-only EXECUTOR_REGISTRY into a full plugin registry.

Each NodePlugin entry adds to the existing executor reference:
  - parameter_schema : JSON Schema for the node's params (used by Bug #1 validator)
  - output_schema    : JSON Schema of the node's output dict (used by condition-key validator)
  - default_params   : Sensible defaults pre-filled by the UI
  - label / icon     : Display metadata for the canvas node

The existing EXECUTOR_REGISTRY in engine/registry.py is NOT replaced â€”
it remains the runtime dispatch table. NodeRegistry wraps it and adds metadata.

Minimum coverage required (RFC-001 Â§3):
  scheduler/cron, gmail/send_email, gmail/get_emails,
  slack/post_message, groq/llm_generate,
  builtin/condition_branch, builtin/set_variable

# TODO: RFC-001 Â§4, Sprint 3 â€” Capability Registry sits alongside NodeRegistry.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Type

logger = logging.getLogger(__name__)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# NodePlugin dataclass
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@dataclass
class NodePlugin:
    """
    Full description of a node type, combining runtime executor reference
    with UI and validation metadata.
    """
    service: str           # e.g. "gmail"
    operation: str         # e.g. "send_email"
    node_type: str         # "trigger" | "action" | "ai_agent" | "condition" | etc.
    label: str             # Human-readable label, e.g. "Send Email"
    icon: str              # Icon name matching the frontend icon set
    executor_class: Type   # The BaseExecutor subclass

    # JSON Schema (draft-07 compatible) for the node's params dict.
    # Used by the condition-key validator and (Sprint 2) Node Inspector.
    parameter_schema: dict = field(default_factory=dict)

    # JSON Schema for the node's output dict (ExecutorResult.output).
    # Used by check_condition_keys to validate downstream template references.
    output_schema: dict = field(default_factory=dict)

    # Sensible param defaults â€” pre-filled when the user adds this node.
    default_params: dict = field(default_factory=dict)

    # Per-node validator callable â€” called by WorkflowValidator after schema check.
    # Signature: validator(node: WorkflowNodeDSL, dsl: WorkflowDSL) -> list[str]
    # Returns a list of error/warning messages (empty = valid).
    validator: Optional[Callable] = None

    doc_url: Optional[str] = None

    # â”€â”€ Display metadata (Sprint 3.5) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    display_name: Optional[str] = None
    """Human-readable override for label in UI. Defaults to label if None."""

    category: str = "general"
    """Grouping category for node palette: email|ai|scheduling|data|logic|messaging|general"""

    color: Optional[str] = None
    """Optional hex color accent for the canvas node card. Falls back to node_type default."""

    tags: List[str] = field(default_factory=list)
    """Searchable tags e.g. ['email', 'send', 'notification']."""

    # â”€â”€ Composition hints (Sprint 3.5) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    recommended_after: List[str] = field(default_factory=list)
    """List of 'service.operation' keys this node is commonly placed after."""

    # â”€â”€ Capability flags â€” metadata only, no behavior (Sprint 3.5) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    supports_streaming: bool = False
    """True if this executor can yield output incrementally (for future streaming UI)."""

    supports_preview: bool = False
    """True if a preview/dry-run is available without full execution."""

    supports_retry: bool = True
    """True if the executor benefits from retry_policy (most action nodes do)."""

    supports_batch: bool = False
    """True if this executor accepts list-typed inputs natively."""

    estimated_latency: str = "medium"
    """Human hint: 'fast' | 'medium' | 'slow'. Used for future UX affordances."""

    # â”€â”€ Auth / OAuth metadata (Sprint 3.5) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    required_scopes: List[str] = field(default_factory=list)
    """OAuth scopes this node requires (e.g. ['gmail.send']). UI hint only â€” not enforced here."""



    @property
    def key(self) -> str:
        """Canonical "service.operation" key used for lookups."""
        return f"{self.service}.{self.operation}"


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# NodeRegistry
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class NodeRegistry:
    """
    Central plugin registry for all node types.

    Usage:
        plugin = NodeRegistry.get("slack", "post_message")
        schema = NodeRegistry.get_parameter_schema("gmail", "get_emails")
        output = NodeRegistry.get_output_schema("gmail", "get_emails")
        all_plugins = NodeRegistry.list_all()
    """

    _plugins: dict[str, NodePlugin] = {}

    @classmethod
    def register(cls, plugin: NodePlugin) -> None:
        """Register a NodePlugin. Later registrations overwrite earlier ones."""
        if plugin.key in cls._plugins:
            logger.debug("[NodeRegistry] Overwriting existing plugin '%s'.", plugin.key)
        cls._plugins[plugin.key] = plugin
        logger.debug("[NodeRegistry] Registered '%s' (%s).", plugin.key, plugin.label)

    @classmethod
    def get(cls, service: str, operation: str) -> Optional[NodePlugin]:
        """Return the NodePlugin for the given service/operation pair, or None."""
        return cls._plugins.get(f"{service}.{operation}")

    @classmethod
    def list_all(cls) -> list[NodePlugin]:
        """Return all registered plugins, sorted by service then operation."""
        return sorted(cls._plugins.values(), key=lambda p: p.key)

    @classmethod
    def get_parameter_schema(cls, service: str, operation: str) -> dict:
        """Return the parameter JSON Schema for the given node type, or {}."""
        plugin = cls.get(service, operation)
        return plugin.parameter_schema if plugin else {}

    @classmethod
    def get_output_schema(cls, service: str, operation: str) -> dict:
        """Return the output JSON Schema for the given node type, or {}."""
        plugin = cls.get(service, operation)
        return plugin.output_schema if plugin else {}


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Plugin registrations â€” minimum RFC-001 Â§3 coverage
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _register_all() -> None:
    """Register all built-in node plugins. Called once at module import time."""

    from backend.workflow.engine.executors.builtin import (
        ConditionBranchExecutor,
        SetVariableExecutor,
        TriggerExecutor,
    )
    from backend.workflow.engine.executors.gmail import (
        GmailGetEmailsExecutor,
        GmailSendEmailExecutor,
    )
    from backend.workflow.engine.executors.slack import SlackPostMessageExecutor
    from backend.workflow.engine.executors.ai_agent import LLMGenerateExecutor

    # â”€â”€ scheduler / cron â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    NodeRegistry.register(NodePlugin(
        service="scheduler",
        operation="cron",
        node_type="trigger",
        label="Scheduled Trigger",
        icon="Clock",
        executor_class=TriggerExecutor,
        doc_url="https://docs.autoflow.ai/nodes/scheduler",
        category="scheduling",
        tags=["trigger", "cron", "schedule", "time", "recurring"],
        estimated_latency="fast",
        supports_retry=False,
        parameter_schema={
            "type": "object",
            "required": ["cron_expression"],
            "properties": {
                "cron_expression": {
                    "type": "string",
                    "description": "Cron expression (5 fields). E.g. '0 9 * * 1' for Mondays at 9 AM.",
                    "pattern": r"^(\S+\s){4}\S+$",
                    "ui": {"widget": "text", "placeholder": "0 9 * * 1", "helpText": "5-field cron: minute hour day month weekday."},
                },
                "timezone": {
                    "type": "string",
                    "default": "UTC",
                    "description": "IANA timezone, e.g. 'America/New_York'.",
                    "ui": {"widget": "text", "placeholder": "UTC", "helpText": "IANA timezone name."},
                },
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "fired_at": {"type": "string", "format": "date-time"},
            },
        },
        default_params={"cron_expression": "0 9 * * 1", "timezone": "UTC"},
    ))

    # â”€â”€ gmail / send_email â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    NodeRegistry.register(NodePlugin(
        service="gmail",
        operation="send_email",
        node_type="action",
        label="Send Email",
        icon="Mail",
        executor_class=GmailSendEmailExecutor,
        doc_url="https://developers.google.com/gmail/api/reference/rest",
        category="email",
        tags=["email", "send", "gmail", "notification", "message"],
        recommended_after=["groq.llm_generate", "builtin.condition_branch"],
        required_scopes=["https://www.googleapis.com/auth/gmail.send"],
        estimated_latency="medium",
        parameter_schema={
            "type": "object",
            "required": ["to", "subject", "body"],
            "properties": {
                "to":      {
                    "type": "string",
                    "description": "Recipient email address(es).",
                    "ui": {"widget": "text", "placeholder": "recipient@example.com", "helpText": "Comma-separate multiple addresses."},
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject line.",
                    "ui": {"widget": "text", "placeholder": "Subject line"},
                },
                "body":    {
                    "type": "string",
                    "description": "Email body (plain text or HTML).",
                    "ui": {"widget": "textarea", "placeholder": "Email body or {{node_id.output.field}}", "helpText": "Supports template variables."},
                },
                "cc":      {
                    "type": "string",
                    "description": "CC recipients (comma-separated).",
                    "ui": {"widget": "text", "placeholder": "cc@example.com"},
                },
                "bcc":     {
                    "type": "string",
                    "description": "BCC recipients (comma-separated).",
                    "ui": {"widget": "text", "placeholder": "bcc@example.com"},
                },
                "credential_id": {
                    "type": "string",
                    "description": "Named Gmail credential (optional).",
                    "ui": {"widget": "credential_select", "helpText": "Leave blank to use your default Gmail connection."},
                },
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "message_id": {"type": "string"},
                "to":         {"type": "string"},
                "subject":    {"type": "string"},
                "status":     {"type": "string", "enum": ["sent"]},
            },
            "required": ["message_id", "to", "subject", "status"],
        },
        default_params={"to": "", "subject": "", "body": ""},
    ))

    # â”€â”€ gmail / get_emails â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    NodeRegistry.register(NodePlugin(
        service="gmail",
        operation="get_emails",
        node_type="action",
        label="Get Emails",
        icon="Inbox",
        executor_class=GmailGetEmailsExecutor,
        doc_url="https://developers.google.com/gmail/api/reference/rest",
        category="email",
        tags=["email", "fetch", "inbox", "gmail", "read", "receive"],
        required_scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        estimated_latency="medium",
        parameter_schema={
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Gmail search query, e.g. 'is:unread from:boss@company.com'.",
                    "ui": {"widget": "text", "placeholder": "is:unread from:example@gmail.com", "helpText": "Standard Gmail search syntax."},
                },
                "max_results": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 100,
                    "ui": {"widget": "number", "helpText": "Maximum emails to fetch (1â€“100)."},
                },
                "credential_id": {
                    "type": "string",
                    "description": "Named Gmail credential (optional).",
                    "ui": {"widget": "credential_select", "helpText": "Leave blank to use your default Gmail connection."},
                },
            },
        },
        # Pinned from gmail.py lines 172 & 202-208 â€” the EXACT output shape.
        output_schema={
            "type": "object",
            "properties": {
                "emails": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id":        {"type": "string"},
                            "thread_id": {"type": "string"},
                            "subject":   {"type": "string"},
                            "from":      {"type": "string"},
                            "to":        {"type": "string"},
                            "date":      {"type": "string"},
                            "snippet":   {"type": "string"},
                            "labels":    {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
                "count": {"type": "integer"},
                "query": {"type": "string"},
            },
            "required": ["emails", "count", "query"],
        },
        default_params={"query": "is:unread", "max_results": 10},
    ))

    # â”€â”€ slack / post_message â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    NodeRegistry.register(NodePlugin(
        service="slack",
        operation="post_message",
        node_type="action",
        label="Post Slack Message",
        icon="MessageSquare",
        executor_class=SlackPostMessageExecutor,
        doc_url="https://api.slack.com/methods/chat.postMessage",
        category="messaging",
        tags=["slack", "notify", "message", "chat", "alert"],
        recommended_after=["groq.llm_generate", "builtin.condition_branch"],
        required_scopes=["chat:write"],
        estimated_latency="fast",
        parameter_schema={
            "type": "object",
            "required": ["channel", "text"],
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Slack channel name (e.g. '#general') or channel ID.",
                    "ui": {"widget": "text", "placeholder": "#general", "helpText": "Use # prefix for channel names."},
                },
                "text":       {
                    "type": "string",
                    "description": "Message text (Slack mrkdwn).",
                    "ui": {"widget": "textarea", "placeholder": "Message text or {{node_id.output.field}}", "helpText": "Supports Slack mrkdwn formatting and template variables."},
                },
                "blocks":     {
                    "type": "array",
                    "description": "Slack Block Kit JSON array.",
                    "ui": {"widget": "json", "helpText": "Optional Block Kit payload. Overrides text if provided."},
                },
                "username":   {
                    "type": "string",
                    "description": "Override bot display name.",
                    "ui": {"widget": "text", "placeholder": "AutoFlow Bot"},
                },
                "icon_emoji": {
                    "type": "string",
                    "description": "Override bot icon emoji.",
                    "ui": {"widget": "text", "placeholder": ":robot_face:"},
                },
                "credential_id": {
                    "type": "string",
                    "description": "Named Slack credential (optional).",
                    "ui": {"widget": "credential_select", "helpText": "Leave blank to use your default Slack connection."},
                },
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "ok":      {"type": "boolean"},
                "channel": {"type": "string"},
                "ts":      {"type": "string"},
                "message": {"type": "string"},
            },
            "required": ["ok"],
        },
        default_params={"channel": "", "text": ""},
    ))

    # â”€â”€ groq / llm_generate â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    NodeRegistry.register(NodePlugin(
        service="groq",
        operation="llm_generate",
        node_type="ai_agent",
        label="AI: Generate Text",
        icon="Sparkles",
        executor_class=LLMGenerateExecutor,
        doc_url="https://console.groq.com/docs/openai",
        category="ai",
        tags=["ai", "llm", "generate", "text", "groq", "language-model"],
        estimated_latency="slow",
        supports_streaming=True,
        parameter_schema={
            "type": "object",
            "required": ["user_prompt"],
            "properties": {
                "user_prompt":   {
                    "type": "string",
                    "description": "The user message to the LLM.",
                    "ui": {"widget": "textarea", "placeholder": "Enter prompt or {{node_id.output.field}}", "helpText": "Supports template variables from previous nodes."},
                },
                "system_prompt": {
                    "type": "string",
                    "description": "System instructions for the LLM.",
                    "ui": {"widget": "textarea", "placeholder": "You are a helpful assistant..."},
                },
                "model": {
                    "type": "string",
                    "default": "llama-3.3-70b-versatile",
                    "description": "Groq model name.",
                    "enum": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"],
                    "ui": {"widget": "select", "helpText": "Choose the Groq model to use."},
                },
                "max_tokens":   {
                    "type": "integer",
                    "default": 1024,
                    "minimum": 1,
                    "ui": {"widget": "number", "helpText": "Maximum tokens in the response."},
                },
                "temperature":  {
                    "type": "number",
                    "default": 0.7,
                    "minimum": 0.0,
                    "maximum": 2.0,
                    "ui": {"widget": "number", "helpText": "0 = deterministic, 2 = very creative."},
                },
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "text":              {"type": "string"},
                "model":             {"type": "string"},
                "prompt_tokens":     {"type": "integer"},
                "completion_tokens": {"type": "integer"},
                "total_tokens":      {"type": "integer"},
            },
            "required": ["text", "model"],
        },
        default_params={
            "model": "llama-3.3-70b-versatile",
            "max_tokens": 1024,
            "temperature": 0.7,
        },
    ))

    # â”€â”€ builtin / condition_branch â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    NodeRegistry.register(NodePlugin(
        service="builtin",
        operation="condition_branch",
        node_type="condition",
        label="Condition / Branch",
        icon="GitBranch",
        executor_class=ConditionBranchExecutor,
        doc_url="https://docs.autoflow.ai/nodes/condition",
        category="logic",
        tags=["condition", "branch", "if", "logic", "route"],
        estimated_latency="fast",
        supports_retry=False,
        parameter_schema={
            "type": "object",
            "required": ["condition"],
            "properties": {
                "condition": {
                    "type": "string",
                    "description": (
                        "Boolean expression using template variables. "
                        "E.g. '{{get_emails_1.output.count > 0}}'. "
                        "May also be a pre-resolved value like 'true' or '5 > 0'."
                    ),
                    "ui": {
                        "widget": "expression",
                        "placeholder": "{{node_id.output.field}} > 0",
                        "helpText": "References output keys from upstream nodes. Apply is required before saving.",
                    },
                },
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "result":    {"type": "boolean"},
                "condition": {"type": "string"},
            },
            "required": ["result", "condition"],
        },
        default_params={"condition": ""},
    ))

    # â”€â”€ builtin / set_variable â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    NodeRegistry.register(NodePlugin(
        service="builtin",
        operation="set_variable",
        node_type="action",
        label="Set Variable",
        icon="Variable",
        executor_class=SetVariableExecutor,
        doc_url="https://docs.autoflow.ai/nodes/set-variable",
        category="data",
        tags=["variable", "set", "transform", "data", "store"],
        estimated_latency="fast",
        supports_retry=False,
        parameter_schema={
            "type": "object",
            "required": ["variable", "value"],
            "properties": {
                "variable": {
                    "type": "string",
                    "description": "Variable name (accessible as {{vars.name}} downstream).",
                    "ui": {"widget": "text", "placeholder": "my_variable", "helpText": "Accessible as {{vars.my_variable}} in downstream nodes."},
                },
                "value": {
                    "description": "Value to set (string, number, or template expression).",
                    "ui": {"widget": "text", "placeholder": "Value or {{node_id.output.field}}"},
                },
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "variable": {"type": "string"},
                "value":    {},
            },
            "required": ["variable", "value"],
        },
        default_params={"variable": "", "value": ""},
    ))


# Register all plugins on module import.
_register_all()

