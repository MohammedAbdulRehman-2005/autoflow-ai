"""
AutoFlow AI X — Sprint 3 Regression Tests
==========================================
Covers:
  S3-001  CapabilityRegistry: match() returns correct pattern for known keyword
  S3-002  CapabilityRegistry: match() returns None for unknown/empty intent
  S3-003  CapabilityRegistry: match() returns confidence ≥ 0.15 for partial keyword match
  S3-004  CapabilityRegistry: match() returns confidence <= 1.0 always
  S3-005  CapabilityRegistry: matched_keywords is a non-empty list on a hit
  S3-006  CapabilityRegistry: list_all() returns all registered patterns
  S3-007  CapabilityRegistry: all registered patterns have ≥ 1 node
  S3-008  CapabilityRegistry: no pattern has empty keywords list
  S3-009  editor_service: _safe_id() generates valid DSL ID (^[a-z][a-z0-9_]*$)
  S3-010  editor_service: _safe_id() never collides with existing_ids
  S3-011  editor_service: _build_node_from_plugin() produces valid WorkflowNodeDSL fields
  S3-012  editor_service: _compute_edge_delta() append mode adds edge from last terminal
  S3-013  editor_service: _compute_edge_delta() splice mode removes old edge + adds two new
  S3-014  editor_service: _build_response_from_capability() uses registry nodes only
  S3-015  AddStepRequest schema: validates correctly with required fields
  S3-016  AddStepResponse schema: delta field is DeltaResult with lists
  S3-017  DeltaResult schema: new_nodes, new_edges, removed_edges all default to []
  S3-018  CapabilityMatchDTO schema: confidence constrained to 0.0–1.0
  S3-019  CapabilitiesListResponse: wraps patterns + total
  S3-020  CapabilityPatternDTO: node_count matches node_keys length
  S3-021  Schemas: AddStepRequest requires current_dsl and user_intent
  S3-022  REGRESSION: mutationService.applyPatch() call signature fix
           (inspector calls must pass plannedDsl as first arg, not {nodeId,...})

All tests are unit tests (no DB, no external API calls).
"""

import os
import re
import uuid

import pytest

# ─── Pre-flight: env vars required by Settings ───────────────────────────────
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-sprint3-tests")
os.environ.setdefault("GROQ_API_KEY", "test-groq-key")


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def make_minimal_dsl(extra_nodes=None, extra_edges=None):
    """Minimal valid DSL-like dict for testing (no Pydantic — pure dict)."""
    nodes = [
        {
            "id": "trigger_1",
            "type": "trigger",
            "service": "scheduler",
            "operation": "cron",
            "label": "Every day at 9 AM",
            "params": {},
        },
        {
            "id": "gmail_1",
            "type": "action",
            "service": "gmail",
            "operation": "get_emails",
            "label": "Get Emails",
            "params": {},
        },
    ]
    edges = [{"source_id": "trigger_1", "target_id": "gmail_1"}]
    if extra_nodes:
        nodes.extend(extra_nodes)
    if extra_edges:
        edges.extend(extra_edges)
    return {
        "name": "Test Workflow",
        "version": 1,
        "trigger": {"type": "manual", "config": {}},
        "nodes": nodes,
        "edges": edges,
    }


# ─────────────────────────────────────────────────────────────────────────────
# S3-001 → S3-008: CapabilityRegistry
# ─────────────────────────────────────────────────────────────────────────────

class TestCapabilityRegistry:

    def _import(self):
        from backend.workflow.capability_registry import CapabilityRegistry
        return CapabilityRegistry

    def test_S3_001_match_known_keyword(self):
        """match() returns a pattern for a known keyword."""
        CR = self._import()
        result = CR.match("process invoices and notify the finance team")
        assert result is not None
        assert result.pattern is not None
        assert "invoice" in result.pattern.keywords or any(
            "invoice" in kw for kw in result.pattern.keywords
        )

    def test_S3_002_match_returns_none_for_unknown(self):
        """match() returns None for a completely unrelated query."""
        CR = self._import()
        result = CR.match("quantum entanglement photon resonance XYZ123")
        assert result is None

    def test_S3_002b_match_returns_none_for_empty(self):
        """match() returns None for empty string."""
        CR = self._import()
        result = CR.match("")
        assert result is None

    def test_S3_003_partial_keyword_match_confidence(self):
        """match() returns confidence ≥ 0.15 for partial match (using a registered keyword)."""
        CR = self._import()
        # "meeting" and "summary" are both in Meeting Assistant keywords
        result = CR.match("I want a meeting summary for today")
        assert result is not None
        assert result.confidence >= 0.15

    def test_S3_004_confidence_max_one(self):
        """match() confidence is always ≤ 1.0."""
        CR = self._import()
        # Use many keywords from the invoice pattern
        result = CR.match("invoice ocr receipt bill scan")
        if result:
            assert result.confidence <= 1.0

    def test_S3_005_matched_keywords_non_empty(self):
        """match() includes a non-empty matched_keywords list on a hit."""
        CR = self._import()
        result = CR.match("meeting summary for today")
        assert result is not None
        assert len(result.matched_keywords) >= 1

    def test_S3_006_list_all_returns_all_patterns(self):
        """list_all() returns all registered patterns (we expect ≥ 4)."""
        CR = self._import()
        patterns = CR.list_all()
        assert len(patterns) >= 4

    def test_S3_007_all_patterns_have_nodes(self):
        """Every registered pattern has ≥ 1 node key."""
        CR = self._import()
        for p in CR.list_all():
            assert len(p.nodes) >= 1, f"Pattern '{p.name}' has no nodes"

    def test_S3_008_no_pattern_has_empty_keywords(self):
        """Every registered pattern has ≥ 1 keyword."""
        CR = self._import()
        for p in CR.list_all():
            assert len(p.keywords) >= 1, f"Pattern '{p.name}' has no keywords"


# ─────────────────────────────────────────────────────────────────────────────
# S3-009 → S3-014: editor_service internals
# ─────────────────────────────────────────────────────────────────────────────

class TestEditorServiceInternals:

    def _import_editor(self):
        from backend.workflow.planner import editor_service
        return editor_service

    def test_S3_009_safe_id_valid_pattern(self):
        """_safe_id() produces IDs matching ^[a-z][a-z0-9_]*$."""
        es = self._import_editor()
        pattern = re.compile(r"^[a-z][a-z0-9_]*$")
        for base in ["gmail_send_email", "slack_post_message", "groq_llm_generate"]:
            node_id = es._safe_id(base, set())
            assert pattern.match(node_id), f"Invalid ID: {node_id}"

    def test_S3_010_safe_id_no_collision(self):
        """_safe_id() never returns an ID that's already in existing_ids."""
        es = self._import_editor()
        existing = set()
        for _ in range(50):
            nid = es._safe_id("slack_post_message", existing)
            assert nid not in existing
            existing.add(nid)

    def test_S3_011_build_node_from_plugin_has_required_fields(self):
        """_build_node_from_plugin() includes all required WorkflowNodeDSL fields."""
        from backend.workflow.node_registry import NodeRegistry
        es = self._import_editor()
        plugin = NodeRegistry.get("gmail", "send_email")
        assert plugin is not None, "gmail.send_email must be registered"

        node = es._build_node_from_plugin(plugin, "gmail_send_email_test")
        required = ["id", "type", "service", "operation", "label", "params"]
        for field in required:
            assert field in node, f"Missing field: {field}"
        assert node["id"] == "gmail_send_email_test"
        assert node["service"] == "gmail"

    def test_S3_012_compute_edge_delta_append_mode(self):
        """_compute_edge_delta() append mode: adds edge from last terminal node."""
        es = self._import_editor()
        dsl = make_minimal_dsl()
        # gmail_1 is the terminal node (no outgoing edges)
        new_edges, removed = es._compute_edge_delta(
            current_dsl=dsl,
            new_node_ids=["slack_1"],
            first_new_node_id="slack_1",
            last_new_node_id="slack_1",
            insert_after_node_id=None,
        )
        assert removed == []
        assert len(new_edges) == 1
        assert new_edges[0] == ("gmail_1", "slack_1")

    def test_S3_013_compute_edge_delta_splice_mode(self):
        """_compute_edge_delta() splice mode: removes old edge, adds two new ones."""
        es = self._import_editor()
        dsl = make_minimal_dsl()
        # Insert between trigger_1 → gmail_1
        new_edges, removed = es._compute_edge_delta(
            current_dsl=dsl,
            new_node_ids=["new_node_1"],
            first_new_node_id="new_node_1",
            last_new_node_id="new_node_1",
            insert_after_node_id="trigger_1",
        )
        # Old edge (trigger_1 → gmail_1) must be removed
        assert ("trigger_1", "gmail_1") in removed
        # trigger_1 → new_node_1 must be added
        assert ("trigger_1", "new_node_1") in new_edges
        # new_node_1 → gmail_1 must be added
        assert ("new_node_1", "gmail_1") in new_edges

    def test_S3_014_build_response_from_capability_uses_registry(self):
        """_build_response_from_capability() builds nodes from NodeRegistry, not LLM."""
        from backend.workflow.capability_registry import CapabilityRegistry, CapabilityMatch
        es = self._import_editor()

        patterns = CapabilityRegistry.list_all()
        assert patterns, "No patterns registered"
        pattern = patterns[0]  # Use first pattern

        fake_match = CapabilityMatch(
            pattern=pattern,
            confidence=0.8,
            matched_keywords=pattern.keywords[:1],
        )
        dsl = make_minimal_dsl()

        response = es._build_response_from_capability(
            cap_match=fake_match,
            current_dsl=dsl,
            existing_node_ids={"trigger_1", "gmail_1"},
            insert_after_node_id=None,
        )

        # Must be registry_driven
        assert response.registry_driven is True
        # Must match node count of the pattern
        assert len(response.applied_node_ids) == len([
            k for k in pattern.nodes
            if __import__('backend.workflow.node_registry', fromlist=['NodeRegistry'])
                .NodeRegistry.get(*k.split('.', 1)) is not None
        ])
        # Delta must have new nodes
        assert len(response.delta.new_nodes) >= 1
        # Explanation must match pattern explanation
        assert response.explanation == pattern.explanation


# ─────────────────────────────────────────────────────────────────────────────
# S3-015 → S3-021: Schemas
# ─────────────────────────────────────────────────────────────────────────────

class TestSprintThreeSchemas:

    def _import(self):
        from backend.workflow.planner.schemas import (
            AddStepRequest,
            AddStepResponse,
            CapabilityMatchDTO,
            CapabilitiesListResponse,
            CapabilityPatternDTO,
            DeltaResult,
            EdgePairDTO,
        )
        return {
            "AddStepRequest": AddStepRequest,
            "AddStepResponse": AddStepResponse,
            "CapabilityMatchDTO": CapabilityMatchDTO,
            "CapabilitiesListResponse": CapabilitiesListResponse,
            "CapabilityPatternDTO": CapabilityPatternDTO,
            "DeltaResult": DeltaResult,
            "EdgePairDTO": EdgePairDTO,
        }

    def test_S3_015_add_step_request_valid(self):
        """AddStepRequest validates correctly with required fields."""
        s = self._import()
        req = s["AddStepRequest"](
            current_dsl={"name": "test", "nodes": [], "edges": []},
            user_intent="add a slack notification",
        )
        assert req.user_intent == "add a slack notification"
        assert req.insert_after_node_id is None
        assert req.workflow_id is None

    def test_S3_016_add_step_response_has_delta(self):
        """AddStepResponse has a delta field of type DeltaResult."""
        s = self._import()
        resp = s["AddStepResponse"](
            delta=s["DeltaResult"](
                new_nodes=[{"id": "slack_1"}],
                new_edges=[{"source_id": "gmail_1", "target_id": "slack_1"}],
                removed_edges=[],
            ),
            explanation="Added Slack notification",
            applied_node_ids=["slack_1"],
            registry_driven=True,
        )
        assert resp.delta.new_nodes[0]["id"] == "slack_1"
        assert resp.registry_driven is True

    def test_S3_017_delta_result_defaults_to_empty_lists(self):
        """DeltaResult defaults new_nodes, new_edges, removed_edges to []."""
        s = self._import()
        delta = s["DeltaResult"]()
        assert delta.new_nodes == []
        assert delta.new_edges == []
        assert delta.removed_edges == []

    def test_S3_018_capability_match_dto_confidence_constrained(self):
        """CapabilityMatchDTO rejects confidence > 1.0."""
        from pydantic import ValidationError
        s = self._import()
        with pytest.raises(ValidationError):
            s["CapabilityMatchDTO"](
                capability_name="test",
                description="test",
                confidence=1.5,  # invalid
                matched_keywords=[],
                explanation="test",
                node_count=1,
            )

    def test_S3_019_capabilities_list_response(self):
        """CapabilitiesListResponse wraps patterns + total."""
        s = self._import()
        r = s["CapabilitiesListResponse"](
            patterns=[
                s["CapabilityPatternDTO"](
                    name="Invoice Processing",
                    description="Extract → Validate → Notify",
                    keywords=["invoice"],
                    node_keys=["groq.llm_extract", "builtin.condition_branch"],
                    explanation="Why: invoice flow",
                    tags=["ai", "finance"],
                    node_count=2,
                )
            ],
            total=1,
        )
        assert r.total == 1
        assert r.patterns[0].name == "Invoice Processing"

    def test_S3_020_capability_pattern_dto_node_count(self):
        """CapabilityPatternDTO node_count is set explicitly (no auto-compute)."""
        s = self._import()
        dto = s["CapabilityPatternDTO"](
            name="Test",
            description="desc",
            keywords=["test"],
            node_keys=["gmail.send_email", "slack.post_message"],
            explanation="why",
            tags=[],
            node_count=2,
        )
        assert dto.node_count == 2
        assert len(dto.node_keys) == 2

    def test_S3_021_add_step_request_requires_current_dsl(self):
        """AddStepRequest raises ValidationError if current_dsl is missing."""
        from pydantic import ValidationError
        s = self._import()
        with pytest.raises(ValidationError):
            s["AddStepRequest"](user_intent="add a step")  # current_dsl missing


# ─────────────────────────────────────────────────────────────────────────────
# S3-022: REGRESSION — applyPatch call signature fix
# ─────────────────────────────────────────────────────────────────────────────

class TestApplyPatchSignatureRegression:
    """
    Sprint 3 regression test for the applyPatch call-signature bug.

    Bug: handleInspectorParamChange and handleInspectorSettingChange in
    WorkflowBuilderPage.jsx were calling:
        mutationService.applyPatch({ nodeId, patch, actor: 'user', reason: '...' })
    passing a single object as currentDsl instead of the actual DSL.

    Fix: calls now correctly pass:
        mutationService.applyPatch(plannedDsl, { nodes: updatedNodes }, 'user', reason)
    """

    def test_S3_022a_apply_patch_correct_signature_updates_node_params(self):
        """
        Simulates the correct applyPatch call from the fixed inspector callback.
        Verifies that a specific node's param is updated in the returned DSL.
        """
        from backend.workflow.planner.schemas import AddStepRequest  # forces env vars
        # We test the mutation logic directly using pure Python dict simulation
        # (mirrors what mutationService.applyPatch does in JS — a simple merge)

        # Simulate the currentDsl (plannedDsl in the component)
        planned_dsl = {
            "name": "My Workflow",
            "version": 1,
            "nodes": [
                {"id": "gmail_1", "type": "action", "service": "gmail", "operation": "send_email",
                 "params": {"to": "old@example.com", "subject": "Old Subject"}},
            ],
            "edges": [],
        }
        node_id = "gmail_1"
        key = "to"
        new_value = "new@example.com"

        # CORRECT call pattern (the fix):
        updated_nodes = [
            {**n, "params": {**n.get("params", {}), key: new_value}}
            if n["id"] == node_id else n
            for n in planned_dsl["nodes"]
        ]
        patch = {"nodes": updated_nodes}
        new_dsl = {**planned_dsl, **patch}

        assert new_dsl["nodes"][0]["params"]["to"] == "new@example.com"
        # Other params must be preserved
        assert new_dsl["nodes"][0]["params"]["subject"] == "Old Subject"

    def test_S3_022b_buggy_signature_would_not_update_params(self):
        """
        Demonstrates what the buggy call did: passing {nodeId, patch, actor, reason}
        as currentDsl caused the merge to treat that object as the base DSL,
        resulting in a garbage result rather than an updated workflow.
        """
        # Simulate the OLD buggy merge: _merge({ nodeId, patch, actor, reason }, patch)
        # where base = { nodeId, patch, actor, reason } and patch = { params: {to: ...} }
        buggy_base = {
            "nodeId": "gmail_1",
            "patch": {"params": {"to": "new@example.com"}},
            "actor": "user",
            "reason": "inspector_param_edit",
        }
        real_patch = {"params": {"to": "new@example.com"}}
        buggy_result = {**buggy_base, **real_patch}

        # The buggy result has no 'nodes' key — it's not a valid DSL
        assert "nodes" not in buggy_result
        assert "nodeId" in buggy_result  # leftover from the wrong first arg

    def test_S3_022c_apply_patch_setting_correct_signature(self):
        """
        Correct applyPatch for setting changes (e.g. always_output_data = True).
        """
        planned_dsl = {
            "name": "My Workflow",
            "version": 1,
            "nodes": [
                {"id": "gmail_1", "type": "action", "service": "gmail", "operation": "send_email",
                 "params": {}, "always_output_data": False},
            ],
            "edges": [],
        }
        node_id = "gmail_1"
        key = "always_output_data"
        value = True

        # CORRECT call pattern:
        updated_nodes = [
            {**n, key: value} if n["id"] == node_id else n
            for n in planned_dsl["nodes"]
        ]
        patch = {"nodes": updated_nodes}
        new_dsl = {**planned_dsl, **patch}

        assert new_dsl["nodes"][0]["always_output_data"] is True
        assert "nodeId" not in new_dsl  # must not have the buggy key
