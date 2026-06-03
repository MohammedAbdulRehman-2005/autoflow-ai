"""
AutoFlow AI X — Graph Validation Check
========================================
Performs structural analysis of the workflow DAG:

  1. Reachability — all nodes must be reachable from the trigger node
  2. Cycle detection — no circular paths (would cause infinite loops)
  3. Dead-end warnings — leaf nodes that are not triggers (advisory)

Algorithms used:
  - Reachability: BFS from trigger node
  - Cycle detection: Kahn's algorithm (topological sort via in-degree tracking)
    If the sorted count < total nodes, a cycle exists.
"""

from collections import deque
from typing import Optional

from backend.workflow.dsl.schema import NodeType, WorkflowDSL
from backend.workflow.validator.models import ErrorCode, ValidationResult


def _build_adjacency(dsl: WorkflowDSL) -> tuple[dict[str, list[str]], dict[str, int]]:
    """
    Build forward adjacency list and in-degree map from DSL edges + on_success/on_failure.

    Returns:
        adj       : { source_id: [target_id, ...] }
        in_degree : { node_id: count_of_incoming_edges }
    """
    node_ids = {n.id for n in dsl.nodes}
    adj: dict[str, list[str]] = {n.id: [] for n in dsl.nodes}
    in_degree: dict[str, int] = {n.id: 0 for n in dsl.nodes}

    def _add_edge(src: str, tgt: str) -> None:
        if src in node_ids and tgt in node_ids and tgt not in adj[src]:
            adj[src].append(tgt)
            in_degree[tgt] += 1

    # Edges from DSL edge list
    for edge in dsl.edges:
        _add_edge(edge.source_id, edge.target_id)

    # Edges from on_success / on_failure pointers
    for node in dsl.nodes:
        if node.on_success:
            _add_edge(node.id, node.on_success)
        if node.on_failure:
            _add_edge(node.id, node.on_failure)

    return adj, in_degree


def check_graph(dsl: WorkflowDSL) -> ValidationResult:
    """Run reachability + cycle detection on the workflow graph."""
    result = ValidationResult()

    # Find the trigger node (schema check already guarantees exactly one)
    trigger_node = next((n for n in dsl.nodes if n.type == NodeType.trigger), None)
    if not trigger_node:
        result.add_error(
            code=ErrorCode.MISSING_TRIGGER_NODE,
            message="Workflow has no trigger node. Exactly one trigger node is required.",
        )
        return result

    adj, in_degree = _build_adjacency(dsl)

    # ── 1. Reachability (BFS from trigger) ────────────────────────────────────
    reachable = _bfs_reachable(trigger_node.id, adj)
    all_node_ids = {n.id for n in dsl.nodes}

    unreachable = all_node_ids - reachable
    for node_id in sorted(unreachable):
        node = next(n for n in dsl.nodes if n.id == node_id)
        result.add_error(
            code=ErrorCode.UNREACHABLE_NODE,
            node_id=node_id,
            message=(
                f"Node '{node.label}' ({node_id}) is unreachable from the trigger. "
                f"Connect it to the workflow or remove it."
            ),
        )

    # ── 2. Cycle detection (Kahn's algorithm) ─────────────────────────────────
    cycle_nodes = _detect_cycles_kahn(adj, in_degree, all_node_ids)
    if cycle_nodes:
        result.add_error(
            code=ErrorCode.CYCLE_DETECTED,
            message=(
                f"Circular dependency detected involving node(s): "
                f"{', '.join(sorted(cycle_nodes))}. "
                f"Workflow graphs must be acyclic (DAG)."
            ),
            detail={"cycle_nodes": sorted(cycle_nodes)},
        )
        # Also flag each node involved in the cycle
        for node_id in sorted(cycle_nodes):
            result.add_error(
                code=ErrorCode.CYCLE_DETECTED,
                node_id=node_id,
                message=f"Node '{node_id}' is part of a circular dependency.",
            )

    # ── 3. Dead-end warnings (non-trigger leaf nodes) ─────────────────────────
    # A node with no outgoing edges (except trigger) is a dead end — warn if
    # it's an action node (it might be intentional for the last step, so just warn)
    for node in dsl.nodes:
        if node.type == NodeType.trigger:
            continue
        if not node.is_disabled and not adj.get(node.id):
            if node.type == NodeType.action:
                result.add_warning(
                    code=ErrorCode.DEAD_END_ACTION_NODE,
                    node_id=node.id,
                    message=(
                        f"Action node '{node.label}' has no outgoing edges. "
                        f"This is the workflow's terminal step."
                    ),
                )

    return result


def _bfs_reachable(start: str, adj: dict[str, list[str]]) -> set[str]:
    """Return the set of all node IDs reachable from `start` via BFS."""
    visited: set[str] = set()
    queue = deque([start])

    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        for neighbor in adj.get(current, []):
            if neighbor not in visited:
                queue.append(neighbor)

    return visited


def _detect_cycles_kahn(
    adj: dict[str, list[str]],
    in_degree: dict[str, int],
    all_nodes: set[str],
) -> set[str]:
    """
    Kahn's topological sort.
    If the number of processed nodes < total nodes, the unprocessed nodes form a cycle.

    Returns the set of node IDs involved in cycles (empty = no cycle).
    """
    # Work with copies so we don't mutate the original
    degree = dict(in_degree)
    queue = deque([n for n in all_nodes if degree[n] == 0])
    processed = 0

    while queue:
        node = queue.popleft()
        processed += 1
        for neighbor in adj.get(node, []):
            degree[neighbor] -= 1
            if degree[neighbor] == 0:
                queue.append(neighbor)

    if processed == len(all_nodes):
        return set()  # No cycle

    # Unprocessed nodes are in cycles
    return {n for n in all_nodes if degree[n] > 0}


def get_topological_order(dsl: WorkflowDSL) -> Optional[list[str]]:
    """
    Return nodes in topological order (trigger first), or None if there's a cycle.
    Used by the template variable checker to determine valid ancestor references.
    """
    adj, in_degree = _build_adjacency(dsl)
    all_nodes = {n.id for n in dsl.nodes}

    degree = dict(in_degree)
    queue = deque([n for n in all_nodes if degree[n] == 0])
    order: list[str] = []

    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbor in adj.get(node, []):
            degree[neighbor] -= 1
            if degree[neighbor] == 0:
                queue.append(neighbor)

    if len(order) != len(all_nodes):
        return None  # Cycle present
    return order


def get_ancestors(node_id: str, dsl: WorkflowDSL, topo_order: list[str]) -> set[str]:
    """
    Return all nodes that can reach `node_id` before it in the graph.
    Uses BFS on the reversed adjacency list.
    """
    adj, _ = _build_adjacency(dsl)

    # Build reverse adjacency
    rev_adj: dict[str, list[str]] = {n.id: [] for n in dsl.nodes}
    for src, targets in adj.items():
        for tgt in targets:
            rev_adj[tgt].append(src)

    return _bfs_reachable(node_id, rev_adj) - {node_id}
