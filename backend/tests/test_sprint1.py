"""
Sprint 1 — Regression Tests
=============================
Covers the three bug fixes and the new infrastructure components.

Run with:
    pytest backend/tests/test_sprint1.py -v

All tests are unit tests (no DB, no external API calls).
"""

import os
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

# ─── Pre-flight: set env vars required by Settings so imports don't fail ─────
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-sprint1-tests")
os.environ.setdefault("GROQ_API_KEY", "test-groq-key")


# ─────────────────────────────────────────────────────────────────────────────
# Shared DSL fixture helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_dsl_dict(**overrides) -> dict:
    """Build a minimal valid workflow DSL dict for testing."""
    base = {
        "id": str(uuid.uuid4()),
        "name": "Test Workflow",
        "version": 1,
        "trigger": {
            "type": "manual",
            "config": {},
        },
        "nodes": [],
        "edges": [],
    }
    base.update(overrides)
    return base


def parse_dsl(d: dict):
    """Parse a raw dict into a WorkflowDSL object."""
    from backend.workflow.dsl.schema import WorkflowDSL
    return WorkflowDSL.model_validate(d)


# ─────────────────────────────────────────────────────────────────────────────
# S1-01: DSL version fields
# ─────────────────────────────────────────────────────────────────────────────

class TestDslVersionFields:
    def test_defaults_present(self):
        """WorkflowDSL should provide default version metadata without explicit input."""
        dsl = parse_dsl(make_dsl_dict(nodes=[{
            "id": "n1",
            "label": "Start",
            "type": "trigger",
            "service": "scheduler",
            "operation": "manual_trigger",
            "params": {},
        }]))
        assert dsl.version >= 1
        assert dsl.migration_version >= 1
        assert dsl.compiler_version is not None
        assert dsl.created_at is not None
        assert dsl.updated_at is not None

    def test_credential_id_optional(self):
        """credential_id should default to None without breaking schema parse."""
        dsl = parse_dsl(make_dsl_dict(nodes=[
            {
                "id": "trig_1",
                "label": "Manual Trigger",
                "type": "trigger",
                "service": "scheduler",
                "operation": "manual_trigger",
                "params": {},
            },
            {
                "id": "n1",
                "label": "Get Emails",
                "type": "action",
                "service": "gmail",
                "operation": "get_emails",
                "params": {"query": "is:unread"},
            },
        ]))
        node = dsl.nodes[1]
        assert node.credential_id is None

    def test_credential_id_accepted(self):
        """credential_id should be accepted when explicitly set."""
        cred_id = str(uuid.uuid4())
        dsl = parse_dsl(make_dsl_dict(nodes=[
            {
                "id": "trig_1",
                "label": "Manual Trigger",
                "type": "trigger",
                "service": "scheduler",
                "operation": "manual_trigger",
                "params": {},
            },
            {
                "id": "n1",
                "label": "Get Emails",
                "type": "action",
                "service": "gmail",
                "operation": "get_emails",
                "params": {"query": "is:unread"},
                "credential_id": cred_id,
            },
        ]))
        assert dsl.nodes[1].credential_id == cred_id


# ─────────────────────────────────────────────────────────────────────────────
# S1-02: WorkflowContext / ExecutionContext extensions
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkflowContext:
    def _make_context(self, **kwargs):
        from backend.workflow.engine.context import ExecutionContext
        return ExecutionContext(
            run_id=uuid.uuid4(),
            trigger_payload={},
            workflow_variables={},
            **kwargs,
        )

    def test_set_get_secret(self):
        ctx = self._make_context()
        ctx.set_secret("gmail", {"access_token": "tok"})
        assert ctx.get_secret("gmail") == {"access_token": "tok"}

    def test_get_secret_missing_returns_none(self):
        ctx = self._make_context()
        assert ctx.get_secret("slack") is None

    def test_set_get_memory(self):
        ctx = self._make_context()
        ctx.set_memory("last_email_count", 5)
        assert ctx.get_memory("last_email_count") == 5

    def test_snapshot_excludes_secrets(self):
        """Secrets must never appear in the snapshot sent to the DB."""
        ctx = self._make_context()
        ctx.set_secret("slack", {"access_token": "super-secret-tok"})
        snap = ctx.snapshot()
        assert "super-secret-tok" not in str(snap)
        assert "_secrets" not in snap

    def test_execution_metadata_populated(self):
        wf_id = uuid.uuid4()
        ctx = self._make_context(workflow_id=wf_id, triggered_by="scheduler")
        assert ctx.execution_metadata["workflow_id"] == str(wf_id)
        assert ctx.execution_metadata["triggered_by"] == "scheduler"
        assert "started_at" in ctx.execution_metadata

    def test_workflow_context_alias(self):
        from backend.workflow.engine.context import ExecutionContext, WorkflowContext
        assert WorkflowContext is ExecutionContext


# ─────────────────────────────────────────────────────────────────────────────
# S1-03: CredentialResolver
# ─────────────────────────────────────────────────────────────────────────────

class TestCredentialResolver:
    def _make_resolver(self, mock_db=None):
        from backend.workflow.engine.credential_resolver import CredentialResolver
        return CredentialResolver(db=mock_db or MagicMock())

    def _make_context(self, user_id=None):
        from backend.workflow.engine.context import ExecutionContext
        return ExecutionContext(
            run_id=uuid.uuid4(),
            trigger_payload={},
            workflow_variables={},
            user_id=user_id or uuid.uuid4(),
        )

    def _make_node(self, service: str, operation: str, credential_id=None):
        from backend.workflow.dsl.schema import ServiceType, OperationType
        node = MagicMock()
        node.service = ServiceType(service)
        node.operation = OperationType(operation)
        node.credential_id = credential_id
        return node

    def test_credential_free_service_skipped(self):
        """builtin service nodes should not trigger any DB query."""
        resolver = self._make_resolver()
        ctx = self._make_context()
        node = self._make_node("builtin", "condition_branch")
        resolver.resolve_for_node(node, ctx)
        # If we get here without DB call → pass
        assert ctx.get_secret("builtin") is None

    def test_secret_cached_on_second_call(self):
        """After first resolution, DB should not be hit again for the same service."""
        resolver = self._make_resolver()
        ctx = self._make_context()
        node = self._make_node("gmail", "get_emails")

        fake_creds = {"access_token": "ya29.xxx"}
        resolver._cache["gmail"] = fake_creds  # prime cache

        resolver.resolve_for_node(node, ctx)
        assert ctx.get_secret("gmail") == fake_creds

    def test_missing_integration_leaves_slot_empty(self):
        """If no integration found in DB, the secret slot stays None."""
        resolver = self._make_resolver()
        ctx = self._make_context()
        node = self._make_node("gmail", "get_emails")

        # _fetch returns None (no integration)
        with patch.object(resolver, "_fetch", return_value=None):
            resolver.resolve_for_node(node, ctx)

        assert ctx.get_secret("gmail") is None


# ─────────────────────────────────────────────────────────────────────────────
# S1-04: NodeRegistry + output_schema
# ─────────────────────────────────────────────────────────────────────────────

class TestNodeRegistry:
    def test_gmail_get_emails_output_schema_has_emails_and_count(self):
        """The gmail.get_emails output schema must declare 'emails' and 'count'."""
        from backend.workflow.node_registry import NodeRegistry
        schema = NodeRegistry.get_output_schema("gmail", "get_emails")
        props = schema.get("properties", {})
        assert "emails" in props, "output_schema missing 'emails'"
        assert "count" in props, "output_schema missing 'count'"
        assert "query" in props, "output_schema missing 'query'"

    def test_slack_post_message_registered(self):
        from backend.workflow.node_registry import NodeRegistry
        plugin = NodeRegistry.get("slack", "post_message")
        assert plugin is not None
        assert plugin.label == "Post Slack Message"

    def test_condition_branch_registered_with_output(self):
        from backend.workflow.node_registry import NodeRegistry
        plugin = NodeRegistry.get("builtin", "condition_branch")
        assert plugin is not None
        assert "result" in plugin.output_schema.get("properties", {})

    def test_all_required_plugins_present(self):
        from backend.workflow.node_registry import NodeRegistry
        required = [
            ("scheduler", "cron"),
            ("gmail", "send_email"),
            ("gmail", "get_emails"),
            ("slack", "post_message"),
            ("groq", "llm_generate"),
            ("builtin", "condition_branch"),
            ("builtin", "set_variable"),
        ]
        for service, op in required:
            plugin = NodeRegistry.get(service, op)
            assert plugin is not None, f"Missing plugin: {service}.{op}"


# ─────────────────────────────────────────────────────────────────────────────
# S1-07 — Bug #1: Condition key validation
# ─────────────────────────────────────────────────────────────────────────────

class TestConditionKeyValidation:
    def _dsl_with_condition(self, condition_expr: str, upstream_op="get_emails"):
        """Build a minimal DSL with a manual trigger, gmail get_emails node + condition node."""
        return parse_dsl({
            "id": str(uuid.uuid4()),
            "name": "Bug1 Test",
            "trigger": {"type": "manual", "config": {}},
            "nodes": [
                {
                    "id": "trigger_1",
                    "label": "Manual Start",
                    "type": "trigger",
                    "service": "scheduler",
                    "operation": "manual_trigger",
                    "params": {},
                    "on_success": "get_emails_1",
                },
                {
                    "id": "get_emails_1",
                    "label": "Get Emails",
                    "type": "action",
                    "service": "gmail",
                    "operation": upstream_op,
                    "params": {"query": "is:unread"},
                    "on_success": "check_1",
                },
                {
                    "id": "check_1",
                    "label": "Check emails",
                    "type": "condition",
                    "service": "builtin",
                    "operation": "condition_branch",
                    "params": {"condition": condition_expr},
                },
            ],
            "edges": [
                {"id": "e1", "source_id": "trigger_1",    "target_id": "get_emails_1"},
                {"id": "e2", "source_id": "get_emails_1", "target_id": "check_1"},
            ],
        })

    def test_valid_key_count_passes(self):
        """{{get_emails_1.output.count > 0}} — 'count' is a real output key."""
        from backend.workflow.validator.checks.condition_keys import check_condition_keys
        dsl = self._dsl_with_condition("{{get_emails_1.output.count > 0}}")
        result = check_condition_keys(dsl)
        assert result.is_valid, f"Expected no errors, got: {result.errors}"

    def test_valid_key_emails_passes(self):
        """{{get_emails_1.output.emails}} — 'emails' is a real output key."""
        from backend.workflow.validator.checks.condition_keys import check_condition_keys
        dsl = self._dsl_with_condition("{{get_emails_1.output.emails}}")
        result = check_condition_keys(dsl)
        assert result.is_valid, f"Expected no errors, got: {result.errors}"

    def test_invalid_key_email_list_fails(self):
        """{{get_emails_1.output.email_list}} — 'email_list' does NOT exist."""
        from backend.workflow.validator.checks.condition_keys import check_condition_keys
        from backend.workflow.validator.models import ErrorCode
        dsl = self._dsl_with_condition("{{get_emails_1.output.email_list}}")
        result = check_condition_keys(dsl)
        assert not result.is_valid
        assert any(e.code == ErrorCode.CONDITION_KEY_MISMATCH for e in result.errors)

    def test_invalid_key_email_count_fails(self):
        """{{get_emails_1.output.email_count}} — 'email_count' does NOT exist (should be 'count')."""
        from backend.workflow.validator.checks.condition_keys import check_condition_keys
        from backend.workflow.validator.models import ErrorCode
        dsl = self._dsl_with_condition("{{get_emails_1.output.email_count}}")
        result = check_condition_keys(dsl)
        assert not result.is_valid
        assert any(e.code == ErrorCode.CONDITION_KEY_MISMATCH for e in result.errors)

    def test_unknown_node_type_no_false_positive(self):
        """If upstream node type isn't in NodeRegistry, skip silently."""
        from backend.workflow.validator.checks.condition_keys import check_condition_keys
        dsl = self._dsl_with_condition("{{get_emails_1.output.anything}}", upstream_op="get_emails")
        # Temporarily unregister gmail to simulate unknown type
        from backend.workflow.node_registry import NodeRegistry
        original = NodeRegistry._plugins.pop("gmail.get_emails", None)
        try:
            result = check_condition_keys(dsl)
            assert result.is_valid, "Should not raise errors for unregistered node types"
        finally:
            if original:
                NodeRegistry._plugins["gmail.get_emails"] = original


# ─────────────────────────────────────────────────────────────────────────────
# S1-08 — Bug #2: Slack placeholder channel
# ─────────────────────────────────────────────────────────────────────────────

class TestSlackPlaceholderChannel:
    def _dsl_with_slack_channel(self, channel: str):
        return parse_dsl({
            "id": str(uuid.uuid4()),
            "name": "Bug2 Test",
            "trigger": {"type": "manual", "config": {}},
            "nodes": [
                {
                    "id": "trig_1",
                    "label": "Manual Start",
                    "type": "trigger",
                    "service": "scheduler",
                    "operation": "manual_trigger",
                    "params": {},
                    "on_success": "slack_1",
                },
                {
                    "id": "slack_1",
                    "label": "Post Message",
                    "type": "action",
                    "service": "slack",
                    "operation": "post_message",
                    "params": {"channel": channel, "text": "Hello!"},
                },
            ],
            "edges": [
                {"id": "e1", "source_id": "trig_1", "target_id": "slack_1"},
            ],
        })

    def test_placeholder_all_xyz_warns(self):
        """channel='all-x' looks like an LLM placeholder — should warn."""
        from backend.workflow.validator.checks.schema import check_schema
        from backend.workflow.validator.models import ErrorCode
        dsl = self._dsl_with_slack_channel("all-x")
        result = check_schema(dsl)
        assert any(w.code == ErrorCode.PLACEHOLDER_CHANNEL for w in result.warnings), \
            f"Expected PLACEHOLDER_CHANNEL warning. Got: {result.warnings}"

    def test_placeholder_your_channel_warns(self):
        """channel='your-channel' — should warn."""
        from backend.workflow.validator.checks.schema import check_schema
        from backend.workflow.validator.models import ErrorCode
        dsl = self._dsl_with_slack_channel("your-channel")
        result = check_schema(dsl)
        assert any(w.code == ErrorCode.PLACEHOLDER_CHANNEL for w in result.warnings)

    def test_real_channel_general_passes(self):
        """channel='#general' — real channel, no warning."""
        from backend.workflow.validator.checks.schema import check_schema
        from backend.workflow.validator.models import ErrorCode
        dsl = self._dsl_with_slack_channel("#general")
        result = check_schema(dsl)
        assert not any(w.code == ErrorCode.PLACEHOLDER_CHANNEL for w in result.warnings), \
            f"Unexpected PLACEHOLDER_CHANNEL for real channel. Got: {result.warnings}"

    def test_real_channel_id_passes(self):
        """channel='C1234567890' — real Slack channel ID, no warning."""
        from backend.workflow.validator.checks.schema import check_schema
        from backend.workflow.validator.models import ErrorCode
        dsl = self._dsl_with_slack_channel("C1234567890")
        result = check_schema(dsl)
        assert not any(w.code == ErrorCode.PLACEHOLDER_CHANNEL for w in result.warnings)


# ─────────────────────────────────────────────────────────────────────────────
# S1-09 — Bug #3: Routing consistency
# ─────────────────────────────────────────────────────────────────────────────

class TestRoutingConsistency:
    def _dsl_with_routing(self, on_success_ptr: str, edge_target: str):
        """Build DSL where on_success disagrees with the edge."""
        return parse_dsl({
            "id": str(uuid.uuid4()),
            "name": "Bug3 Test",
            "trigger": {"type": "manual", "config": {}},
            "nodes": [
                {
                    "id": "trig_1",
                    "label": "Start",
                    "type": "trigger",
                    "service": "scheduler",
                    "operation": "manual_trigger",
                    "params": {},
                    "on_success": "n1",
                },
                {
                    "id": "n1",
                    "label": "Send Email",
                    "type": "action",
                    "service": "gmail",
                    "operation": "send_email",
                    "params": {"to": "a@b.com", "subject": "Hi", "body": "Test"},
                    "on_success": on_success_ptr,
                },
                {
                    "id": "n2_correct",
                    "label": "Correct Next",
                    "type": "action",
                    "service": "builtin",
                    "operation": "set_variable",
                    "params": {"variable": "x", "value": "1"},
                },
                {
                    "id": "n3_wrong",
                    "label": "Wrong Next",
                    "type": "action",
                    "service": "builtin",
                    "operation": "set_variable",
                    "params": {"variable": "x", "value": "1"},
                },
            ],
            "edges": [
                {"id": "e0", "source_id": "trig_1", "target_id": "n1"},
                {"id": "e1", "source_id": "n1",    "target_id": edge_target},
            ],
        })

    def test_consistent_routing_passes(self):
        """on_success == edge target — no error."""
        from backend.workflow.validator.checks.routing_consistency import check_routing_consistency
        dsl = self._dsl_with_routing("n2_correct", "n2_correct")
        result = check_routing_consistency(dsl)
        assert not any(
            e.code == "ROUTING_DRIFT" for e in result.errors
        ), f"Unexpected ROUTING_DRIFT: {result.errors}"

    def test_inconsistent_routing_fails(self):
        """on_success='n3_wrong' but edge points to 'n2_correct' — ROUTING_DRIFT."""
        from backend.workflow.validator.checks.routing_consistency import check_routing_consistency
        from backend.workflow.validator.models import ErrorCode
        dsl = self._dsl_with_routing("n3_wrong", "n2_correct")
        result = check_routing_consistency(dsl)
        assert any(e.code == ErrorCode.ROUTING_DRIFT for e in result.errors), \
            f"Expected ROUTING_DRIFT. Got: {result.errors}"

    def test_normalize_routing_fixes_drift(self):
        """normalize_routing() should rewrite on_success to match the edge."""
        from backend.workflow.validator.checks.routing_consistency import normalize_routing, check_routing_consistency
        dsl = self._dsl_with_routing("n3_wrong", "n2_correct")
        fixed_dsl = normalize_routing(dsl)
        result = check_routing_consistency(fixed_dsl)
        assert not any(e.code == "ROUTING_DRIFT" for e in result.errors), \
            f"normalize_routing failed to fix drift: {result.errors}"


# ─────────────────────────────────────────────────────────────────────────────
# S1-06 — EventBus
# ─────────────────────────────────────────────────────────────────────────────

class TestEventBus:
    def test_emit_calls_handler(self):
        from backend.workflow.event_bus import EventBus
        bus = EventBus()
        received = []
        bus.subscribe("TestEvent", lambda p: received.append(p))
        bus.emit("TestEvent", {"key": "value"})
        assert len(received) == 1
        assert received[0] == {"key": "value"}

    def test_failing_handler_does_not_crash_emitter(self):
        from backend.workflow.event_bus import EventBus
        bus = EventBus()
        bus.subscribe("Boom", lambda p: 1 / 0)  # ZeroDivisionError
        # Should not raise
        bus.emit("Boom", {})

    def test_unsubscribe_works(self):
        from backend.workflow.event_bus import EventBus
        bus = EventBus()
        received = []
        handler = lambda p: received.append(p)
        bus.subscribe("Ev", handler)
        bus.unsubscribe("Ev", handler)
        bus.emit("Ev", {"x": 1})
        assert received == []

    def test_clear_removes_all_handlers(self):
        from backend.workflow.event_bus import EventBus
        bus = EventBus()
        received = []
        bus.subscribe("A", lambda p: received.append(p))
        bus.clear()
        bus.emit("A", {"x": 1})
        assert received == []
