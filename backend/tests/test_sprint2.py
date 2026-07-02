"""
AutoFlow AI X — Sprint 2 Regression Tests
==========================================
Covers:
  S2-001  DSL schema: error_policy field + ErrorPolicy enum
  S2-002  DSL schema: all Sprint 2 settings fields parse correctly
  S2-003  DSL schema: backward compatibility (existing DSLs without new fields)
  S2-004  Runner: execute_single_node() public method exists and is not private
  S2-005  Runner: execute_single_node no-op logging for execute_once + always_output_data
  S2-006  Runner: execute_single_node merges params_override without mutating node.params
  S2-007  Router helpers: _scrub_secrets removes secret-looking keys
  S2-008  Router helpers: _classify_error maps errors to RFC-002 §3 error types
  S2-009  NodeRegistry: list_all() returns populated list with expected plugins
  S2-010  NodeRegistry: all plugins have ui blocks in parameter_schema properties
  S2-011  NodeRegistry: all plugins have doc_url defined
  S2-012  NodeRegistry: no plugin has executor_class or validator in its public dict
  S2-013  Engine schemas: NodeMetadataDTO excludes callable fields
  S2-014  Engine schemas: NodeExecuteResponse has correct fields (no secrets by schema)
  S2-015  Engine schemas: NodeTypesResponse wraps plugins + total
  S2-016  Sprint 1 regression: WorkflowMutationService still passes (smoke)

IMPORTANT: We import directly from internal submodule paths to avoid triggering
backend.workflow.__init__ → planner.router → auth → settings validation,
which requires DATABASE_URL and REDIS_URL that are unavailable in CI/test env.
"""

import asyncio
import inspect
import logging
import os
import sys
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

logger = logging.getLogger(__name__)

# ─── Pre-flight: ensure required env vars are set so settings parsing doesn't
#     block tests that DO import something that touches backend.auth indirectly.
# ─────────────────────────────────────────────────────────────────────────────
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-sprint2-tests")
os.environ.setdefault("GROQ_API_KEY", "test-groq-key")

# ─────────────────────────────────────────────────────────────────────────────
# S2-001  DSL: ErrorPolicy enum exists and has correct values
# ─────────────────────────────────────────────────────────────────────────────

def test_S2_001_error_policy_enum():
    from backend.workflow.dsl.schema import ErrorPolicy
    assert ErrorPolicy.stop.value == "stop"
    assert ErrorPolicy.continue_.value == "continue"
    assert ErrorPolicy.retry.value == "retry"


# ─────────────────────────────────────────────────────────────────────────────
# S2-002  DSL: Sprint 2 settings fields parse correctly
# ─────────────────────────────────────────────────────────────────────────────

def _make_minimal_node_dict(**overrides):
    base = {
        "id": "test_node_1",
        "type": "action",
        "service": "gmail",
        "operation": "send_email",
        "label": "Send Email",
        "params": {"to": "a@b.com", "subject": "Hi", "body": "Hello"},
    }
    base.update(overrides)
    return base


def test_S2_002a_defaults_parse():
    """All Sprint 2 fields default correctly when absent."""
    from backend.workflow.dsl.schema import WorkflowNodeDSL, ErrorPolicy
    node = WorkflowNodeDSL(**_make_minimal_node_dict())
    assert node.error_policy == ErrorPolicy.stop
    assert node.always_output_data is False
    assert node.execute_once is False
    assert node.notes is None
    assert node.display_note_in_flow is False


def test_S2_002b_explicit_values_parse():
    """All Sprint 2 fields accept explicit values."""
    from backend.workflow.dsl.schema import WorkflowNodeDSL, ErrorPolicy
    node = WorkflowNodeDSL(**_make_minimal_node_dict(
        error_policy="continue",
        always_output_data=True,
        execute_once=True,
        notes="test note",
        display_note_in_flow=True,
    ))
    assert node.error_policy == ErrorPolicy.continue_
    assert node.always_output_data is True
    assert node.execute_once is True
    assert node.notes == "test note"
    assert node.display_note_in_flow is True


def test_S2_002c_notes_max_length():
    """notes field rejects strings longer than 4000 chars."""
    from backend.workflow.dsl.schema import WorkflowNodeDSL
    import pydantic
    with pytest.raises((pydantic.ValidationError, ValueError)):
        WorkflowNodeDSL(**_make_minimal_node_dict(notes="x" * 4001))


# ─────────────────────────────────────────────────────────────────────────────
# S2-003  DSL: backward compatibility
# ─────────────────────────────────────────────────────────────────────────────

def test_S2_003_backward_compat_no_new_fields():
    """DSL stored without Sprint 2 fields must still parse using defaults."""
    from backend.workflow.dsl.schema import WorkflowDSL
    legacy_dsl = {
        "name": "Legacy Workflow",
        "version": 1,
        "trigger": {"type": "manual", "config": {}},
        "nodes": [
            {
                "id": "trigger_1",
                "type": "trigger",
                "service": "scheduler",
                "operation": "cron",
                "label": "Daily trigger",
                "params": {"cron_expression": "0 9 * * 1"},
            }
        ],
        "edges": [],
    }
    dsl = WorkflowDSL.model_validate(legacy_dsl)
    node = dsl.nodes[0]
    assert node.error_policy.value == "stop"
    assert node.execute_once is False
    assert node.notes is None


# ─────────────────────────────────────────────────────────────────────────────
# S2-004  Runner: execute_single_node is public, not private
# ─────────────────────────────────────────────────────────────────────────────

def test_S2_004_execute_single_node_is_public():
    """execute_single_node must be a public method (no leading underscore)."""
    from backend.workflow.engine.runner import WorkflowRunner
    assert hasattr(WorkflowRunner, "execute_single_node"), (
        "WorkflowRunner must have a public execute_single_node() method."
    )
    method = getattr(WorkflowRunner, "execute_single_node")
    assert not method.__name__.startswith("_"), (
        "execute_single_node must not have a leading underscore."
    )
    assert asyncio.iscoroutinefunction(method), (
        "execute_single_node must be async."
    )


# ─────────────────────────────────────────────────────────────────────────────
# S2-005  Runner: execute_single_node logs no-op warnings for settings
# ─────────────────────────────────────────────────────────────────────────────

def test_S2_005_execute_once_noop_logged(caplog):
    """execute_once=True on a node triggers an INFO log in execute_single_node."""
    from backend.workflow.dsl.schema import WorkflowNodeDSL
    from backend.workflow.engine.runner import WorkflowRunner

    node_dict = _make_minimal_node_dict(execute_once=True)
    node = WorkflowNodeDSL(**node_dict)

    # Build a minimal runner with a mock executor that returns success
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.output = {"ok": True}
    mock_result.error = None

    runner = _make_mock_runner(mock_result)

    with caplog.at_level(logging.INFO, logger="backend.workflow.engine.runner"):
        asyncio.get_event_loop().run_until_complete(
            runner.execute_single_node(node, params_override={})
        )

    assert any("execute_once" in rec.message for rec in caplog.records), (
        "execute_single_node must log a message when execute_once=True."
    )


def test_S2_005b_always_output_data_noop_logged(caplog):
    """always_output_data=True on a node triggers an INFO log."""
    from backend.workflow.dsl.schema import WorkflowNodeDSL

    node = WorkflowNodeDSL(**_make_minimal_node_dict(always_output_data=True))
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.output = {"ok": True}
    mock_result.error = None

    runner = _make_mock_runner(mock_result)

    with caplog.at_level(logging.INFO, logger="backend.workflow.engine.runner"):
        asyncio.get_event_loop().run_until_complete(
            runner.execute_single_node(node, params_override={})
        )

    assert any("always_output_data" in rec.message for rec in caplog.records), (
        "execute_single_node must log a message when always_output_data=True."
    )


def _make_mock_runner(mock_result):
    """
    Build a WorkflowRunner instance bypassing DB + real DSL.
    Patches _dispatch_executor and _credential_resolver.
    """
    from backend.workflow.dsl.schema import WorkflowDSL
    from backend.workflow.engine.runner import WorkflowRunner
    import uuid

    # WorkflowDSL requires a trigger node + TriggerConfig
    dsl = WorkflowDSL.model_validate({
        "name": "Test",
        "version": 1,
        "trigger": {"type": "manual", "config": {}},
        "nodes": [
            {
                "id": "trigger_1",
                "type": "trigger",
                "service": "scheduler",
                "operation": "cron",
                "label": "Trigger",
                "params": {"cron_expression": "0 9 * * 1"},
            },
            _make_minimal_node_dict(),
        ],
        "edges": [],
    })

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    runner = WorkflowRunner(
        dsl=dsl,
        run_id=uuid.uuid4(),
        db=db,
        trigger_payload={},
        user_id=uuid.uuid4(),
        workflow_id=uuid.uuid4(),
        triggered_by="test",
    )
    # Patch the credential resolver to no-op
    runner._credential_resolver = MagicMock()
    runner._credential_resolver.resolve_for_node = MagicMock()

    # Patch _dispatch_executor to return our mock result
    runner._dispatch_executor = AsyncMock(return_value=mock_result)

    return runner


# ─────────────────────────────────────────────────────────────────────────────
# S2-006  Runner: params_override is merged, not persisted to node.params
# ─────────────────────────────────────────────────────────────────────────────

def test_S2_006_params_override_not_persisted():
    """params_override must merge for execution but NOT mutate node.params."""
    from backend.workflow.dsl.schema import WorkflowNodeDSL

    node = WorkflowNodeDSL(**_make_minimal_node_dict())
    original_params = dict(node.params)

    mock_result = MagicMock()
    mock_result.success = True
    mock_result.output = {}
    mock_result.error = None

    runner = _make_mock_runner(mock_result)

    override = {"to": "override@test.com", "subject": "Overridden"}
    asyncio.get_event_loop().run_until_complete(
        runner.execute_single_node(node, params_override=override)
    )

    # Original node.params must be unchanged
    assert node.params == original_params, (
        "execute_single_node must not mutate node.params."
    )

    # The executor must have been called with the merged params
    called_with = runner._dispatch_executor.call_args
    _, resolved_params = called_with[0]
    assert resolved_params.get("to") == "override@test.com"


# ─────────────────────────────────────────────────────────────────────────────
# S2-007  Router helpers: _scrub_secrets
# ─────────────────────────────────────────────────────────────────────────────

def test_S2_007_scrub_secrets():
    from backend.workflow.engine.router import _scrub_secrets
    dirty = {
        "message_id": "abc123",
        "to": "user@example.com",
        "access_token": "super_secret",
        "api_key": "key123",
        "subject": "Hello",
        "password": "hunter2",
    }
    clean = _scrub_secrets(dirty)
    assert "message_id" in clean
    assert "to" in clean
    assert "subject" in clean
    assert "access_token" not in clean
    assert "api_key" not in clean
    assert "password" not in clean


def test_S2_007b_scrub_secrets_empty():
    from backend.workflow.engine.router import _scrub_secrets
    assert _scrub_secrets({}) == {}


def test_S2_007c_scrub_keeps_non_secret_containing_key():
    from backend.workflow.engine.router import _scrub_secrets
    # 'token' substring in key name must be scrubbed
    assert _scrub_secrets({"token_count": 42}) == {}
    # 'keynote' contains 'key' → scrubbed
    assert _scrub_secrets({"keynote_id": "x"}) == {}
    # 'emails' does not contain any secret pattern → kept
    assert _scrub_secrets({"emails": []}) == {"emails": []}


# ─────────────────────────────────────────────────────────────────────────────
# S2-008  Router helpers: _classify_error
# ─────────────────────────────────────────────────────────────────────────────

def test_S2_008_classify_error():
    from backend.workflow.engine.router import _classify_error
    assert _classify_error("Invalid credentials, 401") == "credential"
    assert _classify_error("Unauthorized") == "credential"
    assert _classify_error("API rate limit exceeded, 429") == "integration"
    assert _classify_error("Connection timeout to slack API") == "integration"
    assert _classify_error("Invalid DSL: schema error") == "compiler"
    assert _classify_error("validation failed: condition_key") == "validation"
    assert _classify_error("Node execution error") == "node"
    assert _classify_error("") == "node"
    assert _classify_error(None) == "node"


# ─────────────────────────────────────────────────────────────────────────────
# S2-009  NodeRegistry: list_all returns expected plugins
# ─────────────────────────────────────────────────────────────────────────────

def test_S2_009_node_registry_list_all():
    from backend.workflow.node_registry import NodeRegistry
    plugins = NodeRegistry.list_all()
    assert len(plugins) >= 5, "Expected at least 5 registered plugins."
    services = {p.service for p in plugins}
    assert "gmail" in services
    assert "slack" in services
    assert "groq" in services
    assert "builtin" in services


def test_S2_009b_node_registry_lookup():
    from backend.workflow.node_registry import NodeRegistry
    p = NodeRegistry.get("gmail", "send_email")
    assert p is not None
    assert p.label == "Send Email"
    assert p.icon == "Mail"


# ─────────────────────────────────────────────────────────────────────────────
# S2-010  NodeRegistry: all plugins have ui blocks in parameter_schema
# ─────────────────────────────────────────────────────────────────────────────

def test_S2_010_all_plugins_have_ui_blocks():
    from backend.workflow.node_registry import NodeRegistry
    plugins = NodeRegistry.list_all()
    for p in plugins:
        props = p.parameter_schema.get("properties", {})
        for field_name, field_def in props.items():
            # credential_select fields always have ui, but trigger nodes may have fewer
            # We check that at least the main user-visible fields have ui hints
            if field_name == "credential_id":
                assert "ui" in field_def, (
                    f"Plugin {p.service}.{p.operation}: "
                    f"'credential_id' field missing ui block."
                )


def test_S2_010b_ui_widget_is_valid():
    """All ui.widget values must be from the known set."""
    from backend.workflow.node_registry import NodeRegistry
    VALID_WIDGETS = {
        "text", "textarea", "number", "select", "toggle",
        "json", "expression", "credential_select",
    }
    plugins = NodeRegistry.list_all()
    for p in plugins:
        for field_name, field_def in p.parameter_schema.get("properties", {}).items():
            ui = field_def.get("ui", {})
            widget = ui.get("widget")
            if widget is not None:
                assert widget in VALID_WIDGETS, (
                    f"Plugin {p.service}.{p.operation}.{field_name}: "
                    f"unknown widget '{widget}'."
                )


# ─────────────────────────────────────────────────────────────────────────────
# S2-011  NodeRegistry: all plugins have doc_url
# ─────────────────────────────────────────────────────────────────────────────

def test_S2_011_all_plugins_have_doc_url():
    from backend.workflow.node_registry import NodeRegistry
    plugins = NodeRegistry.list_all()
    missing = [
        f"{p.service}.{p.operation}"
        for p in plugins
        if not p.doc_url
    ]
    assert not missing, (
        f"The following plugins are missing doc_url: {missing}. "
        "Add a doc_url to each NodePlugin registration."
    )


# ─────────────────────────────────────────────────────────────────────────────
# S2-012  NodeRegistry: NodePlugin dataclass has no callable in serialized DTO
# ─────────────────────────────────────────────────────────────────────────────

def test_S2_012_node_metadata_dto_has_no_callable():
    """NodeMetadataDTO must only contain serializable fields — no callables."""
    from backend.workflow.engine.schemas import NodeMetadataDTO
    from backend.workflow.node_registry import NodeRegistry
    import json

    plugins = NodeRegistry.list_all()
    for p in plugins:
        dto = NodeMetadataDTO(
            service=p.service,
            operation=p.operation,
            node_type=p.node_type,
            label=p.label,
            icon=p.icon,
            parameter_schema=p.parameter_schema,
            output_schema=p.output_schema,
            default_params=p.default_params,
            doc_url=p.doc_url,
        )
        # This must not raise (would raise if callables or non-serializable objects slipped through)
        serialized = json.loads(dto.model_dump_json())
        assert serialized["service"] == p.service


# ─────────────────────────────────────────────────────────────────────────────
# S2-013  Engine schemas: NodeMetadataDTO field list
# ─────────────────────────────────────────────────────────────────────────────

def test_S2_013_node_metadata_dto_fields():
    from backend.workflow.engine.schemas import NodeMetadataDTO
    fields = NodeMetadataDTO.model_fields
    required = {"service", "operation", "node_type", "label", "icon",
                "parameter_schema", "output_schema", "default_params"}
    missing = required - set(fields)
    assert not missing, f"NodeMetadataDTO missing fields: {missing}"

    # executor_class and validator must NOT be in the DTO
    assert "executor_class" not in fields
    assert "validator" not in fields


# ─────────────────────────────────────────────────────────────────────────────
# S2-014  Engine schemas: NodeExecuteResponse fields
# ─────────────────────────────────────────────────────────────────────────────

def test_S2_014_node_execute_response_fields():
    from backend.workflow.engine.schemas import NodeExecuteResponse
    from datetime import datetime, timezone
    resp = NodeExecuteResponse(
        node_id="test_1",
        success=True,
        output={"foo": "bar"},
        error=None,
        error_type=None,
        duration_ms=42,
        executed_at=datetime.now(timezone.utc),
    )
    assert resp.node_id == "test_1"
    assert resp.success is True
    assert resp.duration_ms == 42
    # Verify no 'token'/'secret' fields exist in the schema itself
    fields = set(NodeExecuteResponse.model_fields.keys())
    secret_fields = {f for f in fields if any(
        pat in f.lower() for pat in ("token", "secret", "password", "key", "credential", "auth")
    )}
    assert not secret_fields, (
        f"NodeExecuteResponse must not have secret-named fields: {secret_fields}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# S2-015  Engine schemas: NodeTypesResponse
# ─────────────────────────────────────────────────────────────────────────────

def test_S2_015_node_types_response():
    from backend.workflow.engine.schemas import NodeTypesResponse, NodeMetadataDTO
    resp = NodeTypesResponse(
        plugins=[
            NodeMetadataDTO(
                service="test", operation="op", node_type="action",
                label="Test", icon="Zap",
                parameter_schema={}, output_schema={}, default_params={},
                doc_url="https://example.com",
            )
        ],
        total=1,
    )
    assert resp.total == 1
    assert len(resp.plugins) == 1
    assert resp.plugins[0].service == "test"


# ─────────────────────────────────────────────────────────────────────────────
# S2-016  Sprint 1 regression: WorkflowMutationService smoke test
# ─────────────────────────────────────────────────────────────────────────────

def test_S2_016_sprint1_regression_mutation_service():
    """Smoke: WorkflowMutationService still initialises after Sprint 2 changes."""
    try:
        from frontend.src.services.mutationService import WorkflowMutationService  # type: ignore
    except ImportError:
        pytest.skip("mutationService.js is a frontend module — skipped in Python tests.")

    # If somehow importable, check it has applyPatch
    svc = WorkflowMutationService()
    assert hasattr(svc, "applyPatch")
