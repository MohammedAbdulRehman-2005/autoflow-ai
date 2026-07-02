"""
AutoFlow AI X — Routing Consistency Check  (Bug #3 fix)
=========================================================
Detects divergence between node.on_success/on_failure pointers and the
DSL edges array — the "dual routing sources" problem.

Background:
  WorkflowNodeDSL has both:
    - node.on_success / node.on_failure  (shorthand pointers)
    - dsl.edges[]                        (the canonical edge list)

  The runner uses on_success/on_failure for standard nodes and edges (with
  labels) for condition routing. If they disagree, behaviour is undefined.

  Pre-flight finding: the runner model does NOT support fan-out (one source
  → multiple unconditional targets). on_success is a single str, not a list.
  Therefore `_normalize_routing` taking success_edges[0] is safe — there's
  at most one unconditional edge per source in valid DSLs.

This check:
  1. For each node, derives the expected on_success from unconditional edges
     (edges with no label, or label "true" for condition nodes).
  2. Derives expected on_failure from failure edges (label "false" or "error").
  3. If node.on_success is set AND doesn't match what edges say → ROUTING_DRIFT.
  4. If node.on_failure is set AND doesn't match what edges say → ROUTING_DRIFT.

The fix for existing DSLs is in WorkflowMutationService._normalize_routing()
which keeps them in sync on every patch. This check is the gate that prevents
future drift.
"""

import logging
from typing import Optional

from backend.workflow.dsl.schema import NodeType, WorkflowDSL
from backend.workflow.validator.models import ErrorCode, ValidationResult

logger = logging.getLogger(__name__)

# Edge labels that represent the failure/false branch
_FAILURE_LABELS = frozenset({"false", "no", "error", "fail", "failure"})
# Edge labels that represent the success/true branch
_SUCCESS_LABELS = frozenset({"true", "yes", "success"})


def check_routing_consistency(dsl: WorkflowDSL) -> ValidationResult:
    """
    Verify that node.on_success and node.on_failure agree with the edges array.
    Emits ROUTING_DRIFT errors where they disagree.
    """
    result = ValidationResult()

    # Build per-source edge lists
    edges_from: dict[str, list] = {}
    for edge in dsl.edges:
        edges_from.setdefault(edge.source_id, []).append(edge)

    for node in dsl.nodes:
        if node.is_disabled:
            continue

        outgoing = edges_from.get(node.id, [])
        if not outgoing:
            # No edges — on_success/on_failure should also be None.
            # If they're set, that's a soft inconsistency but not actionable
            # without edges (graph check will catch UNREACHABLE_NODE instead).
            continue

        # ── Derive expected on_success from edges ─────────────────────────────
        # For condition nodes: edge with label "true" / "yes"
        # For standard nodes:  edge with no label (or label "true")
        if node.type == NodeType.condition:
            success_candidates = [
                e for e in outgoing
                if e.label and e.label.lower() in _SUCCESS_LABELS
            ]
        else:
            # Standard node: unconditional edge (no label) or labelled "true"
            success_candidates = [
                e for e in outgoing
                if not e.label or e.label.lower() in _SUCCESS_LABELS
            ]

        expected_on_success: Optional[str] = (
            success_candidates[0].target_id if success_candidates else None
        )

        # ── Derive expected on_failure from edges ─────────────────────────────
        failure_candidates = [
            e for e in outgoing
            if e.label and e.label.lower() in _FAILURE_LABELS
        ]
        expected_on_failure: Optional[str] = (
            failure_candidates[0].target_id if failure_candidates else None
        )

        # ── Check on_success ──────────────────────────────────────────────────
        if (
            node.on_success is not None
            and expected_on_success is not None
            and node.on_success != expected_on_success
        ):
            result.add_error(
                code=ErrorCode.ROUTING_DRIFT,
                node_id=node.id,
                message=(
                    f"Node '{node.label}' ({node.id}): on_success points to "
                    f"'{node.on_success}' but the edges array routes success to "
                    f"'{expected_on_success}'. These must agree — edges are canonical."
                ),
                detail={
                    "node_id":            node.id,
                    "on_success_pointer": node.on_success,
                    "edge_target":        expected_on_success,
                },
            )

        # ── Check on_failure ──────────────────────────────────────────────────
        if (
            node.on_failure is not None
            and expected_on_failure is not None
            and node.on_failure != expected_on_failure
        ):
            result.add_error(
                code=ErrorCode.ROUTING_DRIFT,
                node_id=node.id,
                message=(
                    f"Node '{node.label}' ({node.id}): on_failure points to "
                    f"'{node.on_failure}' but the edges array routes failure to "
                    f"'{expected_on_failure}'. These must agree — edges are canonical."
                ),
                detail={
                    "node_id":            node.id,
                    "on_failure_pointer": node.on_failure,
                    "edge_target":        expected_on_failure,
                },
            )

    return result


def normalize_routing(dsl: WorkflowDSL) -> WorkflowDSL:
    """
    Derive on_success/on_failure from edges and write them back to each node,
    ensuring the two sources of truth stay in sync.

    Called by WorkflowMutationService on every patch so drift cannot accumulate.

    Pre-flight confirmed: the runner model does not support fan-out (on_success
    is a single str), so taking success_edges[0] is safe for valid DSLs.
    Invalid fan-out DSLs are caught by the graph validator before reaching here.
    """
    edges_from: dict[str, list] = {}
    for edge in dsl.edges:
        edges_from.setdefault(edge.source_id, []).append(edge)

    for node in dsl.nodes:
        outgoing = edges_from.get(node.id, [])

        if node.type == NodeType.condition:
            success_edges = [
                e for e in outgoing
                if e.label and e.label.lower() in _SUCCESS_LABELS
            ]
        else:
            success_edges = [
                e for e in outgoing
                if not e.label or e.label.lower() in _SUCCESS_LABELS
            ]

        failure_edges = [
            e for e in outgoing
            if e.label and e.label.lower() in _FAILURE_LABELS
        ]

        node.on_success = success_edges[0].target_id if success_edges else node.on_success
        node.on_failure = failure_edges[0].target_id if failure_edges else node.on_failure

    return dsl
