"""
AutoFlow AI X — Node Registry  (RFC-001 §3)
=============================================
Promotes the executor-only EXECUTOR_REGISTRY into a full plugin registry.

Each NodePlugin entry adds to the existing executor reference:
  - parameter_schema : JSON Schema for the node's params (used by Bug #1 validator)
  - output_schema    : JSON Schema of the node's output dict (used by condition-key validator)
  - default_params   : Sensible defaults pre-filled by the UI
  - label / icon     : Display metadata for the canvas node

The existing EXECUTOR_REGISTRY in engine/registry.py is NOT replaced —
it remains the runtime dispatch table. NodeRegistry wraps it and adds metadata.

Minimum coverage required (RFC-001 §3):
  scheduler/cron, gmail/send_email, gmail/get_emails,
  slack/post_message, groq/llm_generate,
  builtin/condition_branch, builtin/set_variable

# TODO: RFC-001 §4, Sprint 3 — Capability Registry sits alongside NodeRegistry.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Type

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# NodePlugin dataclass
# ─────────────────────────────────────────────────────────────────────────────

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

    # Sensible param defaults — pre-filled when the user adds this node.
    default_params: dict = field(default_factory=dict)

    # Per-node validator callable — called by WorkflowValidator after schema check.
    # Signature: validator(node: WorkflowNodeDSL, dsl: WorkflowDSL) -> list[str]
    # Returns a list of error/warning messages (empty = valid).
    validator: Optional[Callable] = None

    doc_url: Optional[str] = None

    @property
    def key(self) -> str:
        """Canonical "service.operation" key used for lookups."""
        return f"{self.service}.{self.operation}"


# ─────────────────────────────────────────────────────────────────────────────
# NodeRegistry
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# Plugin registrations — minimum RFC-001 §3 coverage
# ─────────────────────────────────────────────────────────────────────────────

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

    # ── scheduler / cron ────────────────────────────────────────────────────
    NodeRegistry.register(NodePlugin(
        service="scheduler",
        operation="cron",
        node_type="trigger",
        label="Scheduled Trigger",
        icon="Clock",
        executor_class=TriggerExecutor,
        parameter_schema={
            "type": "object",
            "required": ["cron_expression"],
            "properties": {
                "cron_expression": {
                    "type": "string",
                    "description": "Cron expression (5 fields). E.g. '0 9 * * 1' for Mondays at 9 AM.",
                    "pattern": r"^(\S+\s){4}\S+$",
                },
                "timezone": {
                    "type": "string",
                    "default": "UTC",
                    "description": "IANA timezone, e.g. 'America/New_York'.",
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

    # ── gmail / send_email ───────────────────────────────────────────────────
    NodeRegistry.register(NodePlugin(
        service="gmail",
        operation="send_email",
        node_type="action",
        label="Send Email",
        icon="Mail",
        executor_class=GmailSendEmailExecutor,
        parameter_schema={
            "type": "object",
            "required": ["to", "subject", "body"],
            "properties": {
                "to":      {"type": "string", "description": "Recipient email address(es)."},
                "subject": {"type": "string", "description": "Email subject line."},
                "body":    {"type": "string", "description": "Email body (plain text or HTML)."},
                "cc":      {"type": "string", "description": "CC recipients (comma-separated)."},
                "bcc":     {"type": "string", "description": "BCC recipients (comma-separated)."},
                "credential_id": {"type": "string", "description": "Named Gmail credential (optional)."},
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

    # ── gmail / get_emails ───────────────────────────────────────────────────
    NodeRegistry.register(NodePlugin(
        service="gmail",
        operation="get_emails",
        node_type="action",
        label="Get Emails",
        icon="Inbox",
        executor_class=GmailGetEmailsExecutor,
        parameter_schema={
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Gmail search query, e.g. 'is:unread from:boss@company.com'.",
                },
                "max_results": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 100,
                },
                "credential_id": {"type": "string", "description": "Named Gmail credential (optional)."},
            },
        },
        # Pinned from gmail.py lines 172 & 202-208 — the EXACT output shape.
        # Bug #1 validator uses this to catch condition expressions referencing
        # non-existent keys (e.g. output.email_list which doesn't exist;
        # the real key is output.emails).
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

    # ── slack / post_message ─────────────────────────────────────────────────
    NodeRegistry.register(NodePlugin(
        service="slack",
        operation="post_message",
        node_type="action",
        label="Post Slack Message",
        icon="MessageSquare",
        executor_class=SlackPostMessageExecutor,
        parameter_schema={
            "type": "object",
            "required": ["channel", "text"],
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Slack channel name (e.g. '#general') or channel ID.",
                },
                "text":       {"type": "string", "description": "Message text (Slack mrkdwn)."},
                "blocks":     {"type": "array",  "description": "Slack Block Kit JSON array."},
                "username":   {"type": "string", "description": "Override bot display name."},
                "icon_emoji": {"type": "string", "description": "Override bot icon emoji."},
                "credential_id": {"type": "string", "description": "Named Slack credential (optional)."},
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

    # ── groq / llm_generate ──────────────────────────────────────────────────
    NodeRegistry.register(NodePlugin(
        service="groq",
        operation="llm_generate",
        node_type="ai_agent",
        label="AI: Generate Text",
        icon="Sparkles",
        executor_class=LLMGenerateExecutor,
        parameter_schema={
            "type": "object",
            "required": ["user_prompt"],
            "properties": {
                "user_prompt":   {"type": "string", "description": "The user message to the LLM."},
                "system_prompt": {"type": "string", "description": "System instructions for the LLM."},
                "model": {
                    "type": "string",
                    "default": "llama-3.3-70b-versatile",
                    "description": "Groq model name.",
                },
                "max_tokens":   {"type": "integer", "default": 1024, "minimum": 1},
                "temperature":  {"type": "number",  "default": 0.7, "minimum": 0.0, "maximum": 2.0},
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

    # ── builtin / condition_branch ───────────────────────────────────────────
    NodeRegistry.register(NodePlugin(
        service="builtin",
        operation="condition_branch",
        node_type="condition",
        label="Condition / Branch",
        icon="GitBranch",
        executor_class=ConditionBranchExecutor,
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

    # ── builtin / set_variable ───────────────────────────────────────────────
    NodeRegistry.register(NodePlugin(
        service="builtin",
        operation="set_variable",
        node_type="action",
        label="Set Variable",
        icon="Variable",
        executor_class=SetVariableExecutor,
        parameter_schema={
            "type": "object",
            "required": ["variable", "value"],
            "properties": {
                "variable": {
                    "type": "string",
                    "description": "Variable name (accessible as {{vars.name}} downstream).",
                },
                "value": {
                    "description": "Value to set (string, number, or template expression).",
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
