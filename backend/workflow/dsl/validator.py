"""
AutoFlow AI X — DSL Graph Validator
=====================================
Runs semantic validation on a WorkflowDSL object that Pydantic alone cannot
catch. This is the "second layer" of validation, run after Pydantic parsing.

Checks performed:
  1. Cycle detection — workflow graph must be a DAG (Directed Acyclic Graph)
  2. Reachability  — all nodes must be reachable from the trigger node
  3. Dead ends     — action/loop nodes with no outbound edges are flagged as warnings
  4. Condition integrity — condition nodes must have exactly 2 outbound edges
  5. Loop body     — loop nodes must have at least one outbound edge (the loop body)
"""

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Set

from backend.workflow.dsl.schema import NodeType, WorkflowDSL, WorkflowNodeDSL


@dataclass
class ValidationResult:
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.is_valid = False

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def _build_adjacency(dsl: WorkflowDSL) -> Dict[str, List[str]]:
    """Build forward adjacency list from edges + on_success/on_failure links."""
    adj: Dict[str, List[str]] = defaultdict(list)
    for node in dsl.nodes:
        # Ensure every node has an entry even with no outbound edges
        adj[node.id]  # triggers defaultdict entry

    for edge in dsl.edges:
        adj[edge.source_id].append(edge.target_id)

    # Also respect on_success / on_failure (they may duplicate edges — that's ok)
    for node in dsl.nodes:
        if node.on_success and node.on_success not in adj[node.id]:
            adj[node.id].append(node.on_success)
        if node.on_failure and node.on_failure not in adj[node.id]:
            adj[node.id].append(node.on_failure)

    return dict(adj)


def _detect_cycle(adj: Dict[str, List[str]], node_ids: Set[str]) -> List[str]:
    """
    DFS-based cycle detection (Kahn's algorithm variant).
    Returns a list of node IDs that form part of a cycle, or empty list if DAG.
    """
    in_degree: Dict[str, int] = {n: 0 for n in node_ids}
    for src, targets in adj.items():
        for tgt in targets:
            in_degree[tgt] = in_degree.get(tgt, 0) + 1

    queue = deque([n for n, d in in_degree.items() if d == 0])
    visited_count = 0

    while queue:
        node = queue.popleft()
        visited_count += 1
        for neighbor in adj.get(node, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if visited_count < len(node_ids):
        # Nodes still with in_degree > 0 are in a cycle
        return [n for n, d in in_degree.items() if d > 0]
    return []


def _find_reachable_nodes(adj: Dict[str, List[str]], start: str) -> Set[str]:
    """BFS from the trigger node to find all reachable node IDs."""
    visited: Set[str] = set()
    queue = deque([start])
    while queue:
        node = queue.popleft()
        if node in visited:
            continue
        visited.add(node)
        for neighbor in adj.get(node, []):
            if neighbor not in visited:
                queue.append(neighbor)
    return visited


def validate_workflow_graph(dsl: WorkflowDSL) -> ValidationResult:
    """
    Run all semantic graph checks on a WorkflowDSL that has already passed
    Pydantic validation. Returns a ValidationResult with errors and warnings.
    """
    result = ValidationResult()
    node_map: Dict[str, WorkflowNodeDSL] = {n.id: n for n in dsl.nodes}
    node_ids: Set[str] = set(node_map.keys())
    adj = _build_adjacency(dsl)

    # ── 1. Cycle Detection ────────────────────────────────────────────────────
    cycle_nodes = _detect_cycle(adj, node_ids)
    if cycle_nodes:
        result.add_error(
            f"Cycle detected. The following nodes form a circular dependency "
            f"which would cause an infinite loop: {cycle_nodes}. "
            f"Use a 'delay' node or break the cycle."
        )

    # ── 2. Find the trigger node ──────────────────────────────────────────────
    trigger_nodes = [n for n in dsl.nodes if n.type == NodeType.trigger]
    if not trigger_nodes:
        result.add_error("No trigger node found. Cannot determine graph entry point.")
        return result  # Cannot continue without entry point

    trigger_id = trigger_nodes[0].id

    # ── 3. Reachability Check ─────────────────────────────────────────────────
    reachable = _find_reachable_nodes(adj, trigger_id)
    unreachable = node_ids - reachable
    if unreachable:
        result.add_error(
            f"Unreachable nodes detected: {sorted(unreachable)}. "
            f"These nodes will never be executed. Connect them to the workflow or remove them."
        )

    # ── 4. Condition Node Integrity ───────────────────────────────────────────
    for node in dsl.nodes:
        if node.type == NodeType.condition:
            outbound_edges = [e for e in dsl.edges if e.source_id == node.id]
            if len(outbound_edges) < 2:
                result.add_error(
                    f"Condition node '{node.id}' ({node.label!r}) must have exactly 2 outbound "
                    f"edges (one for 'true', one for 'false'), but has {len(outbound_edges)}."
                )
            elif len(outbound_edges) > 2:
                result.add_warning(
                    f"Condition node '{node.id}' has {len(outbound_edges)} outbound edges. "
                    f"Only 2 are expected (true/false). Additional edges may be ignored."
                )

    # ── 5. Loop Node Integrity ────────────────────────────────────────────────
    for node in dsl.nodes:
        if node.type == NodeType.loop:
            outbound_edges = [e for e in dsl.edges if e.source_id == node.id]
            if not outbound_edges and not node.on_success:
                result.add_error(
                    f"Loop node '{node.id}' ({node.label!r}) has no outbound edges. "
                    f"A loop must define what to execute for each item."
                )

    # ── 6. Dead-End Warnings ──────────────────────────────────────────────────
    for node in dsl.nodes:
        if node.type in (NodeType.trigger, NodeType.condition, NodeType.loop):
            continue  # These are expected to have specific routing rules
        outbound = adj.get(node.id, [])
        if not outbound and not node.on_success and not node.on_failure:
            result.add_warning(
                f"Node '{node.id}' ({node.label!r}) is a terminal node with no "
                f"outbound connections. Execution will stop here."
            )

    # ── 7. Disabled Nodes Warning ─────────────────────────────────────────────
    disabled = [n.id for n in dsl.nodes if n.is_disabled]
    if disabled:
        result.add_warning(
            f"The following nodes are disabled and will be skipped at runtime: {disabled}"
        )

    return result
