"""
AutoFlow AI X — Template Variable Validation Check
=====================================================
Scans every node's params for {{...}} references and validates that:

  1. System namespaces (trigger, context, env, vars, item, run) are always valid
  2. `{{vars.key}}` references actually exist in workflow.variables
  3. `{{node_id.field}}` references point to a node that EXISTS in the workflow
  4. `{{node_id.field}}` references point to an ANCESTOR node (runs before current)
     — forward references (to nodes that may not have run yet) are warnings, not errors
  5. `{{item.field}}` is only valid inside a loop body

Algorithm:
  - Parse all {{...}} patterns from params (recursive dict/list walk)
  - Build topological order to determine ancestor relationships
  - For each reference, classify source and validate
"""

import re
from typing import Any, Optional

from backend.workflow.dsl.schema import NodeType, WorkflowDSL
from backend.workflow.validator.checks.graph import get_ancestors, get_topological_order
from backend.workflow.validator.models import ErrorCode, ValidationResult

# Regex to extract all {{ expression }} blocks
TEMPLATE_PATTERN = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")

# Reserved namespaces that are always valid — no validation needed
ALWAYS_VALID_NAMESPACES = {"trigger", "context", "env", "run"}


def _extract_all_references(value: Any) -> list[str]:
    """
    Recursively walk a value (str/dict/list) and extract all {{...}} expression strings.
    Returns the raw expression content (stripped), e.g. "node_id.output.field".
    """
    refs: list[str] = []
    if isinstance(value, str):
        for match in TEMPLATE_PATTERN.finditer(value):
            refs.append(match.group(1).strip())
    elif isinstance(value, dict):
        for v in value.values():
            refs.extend(_extract_all_references(v))
    elif isinstance(value, list):
        for item in value:
            refs.extend(_extract_all_references(item))
    return refs


def _parse_ref_namespace(ref: str) -> tuple[str, str]:
    """
    Split a template reference into (namespace, rest).
    E.g. "node_id.output.count"  → ("node_id", "output.count")
         "trigger.payload.email" → ("trigger", "payload.email")
         "context.today"         → ("context", "today")
         "vars.sheet_id"         → ("vars", "sheet_id")
    """
    parts = ref.split(".", 1)
    namespace = parts[0]
    rest = parts[1] if len(parts) > 1 else ""
    return namespace, rest


def _is_inside_loop(node_id: str, dsl: WorkflowDSL, topo_order: list[str]) -> bool:
    """
    Returns True if `node_id` is in the body of a loop (i.e., a loop node is among its ancestors).
    """
    loop_node_ids = {n.id for n in dsl.nodes if n.type == NodeType.loop}
    if not loop_node_ids:
        return False
    ancestors = get_ancestors(node_id, dsl, topo_order)
    return bool(ancestors & loop_node_ids)


def check_template_vars(dsl: WorkflowDSL) -> ValidationResult:
    """
    Validate all template variable references across all nodes.
    """
    result = ValidationResult()
    all_node_ids = {n.id for n in dsl.nodes}

    # Build topological order (needed for ancestor checks)
    topo_order = get_topological_order(dsl)
    if topo_order is None:
        # Graph has cycles — skip template check (cycle errors reported elsewhere)
        result.add_warning(
            code=ErrorCode.UNDEFINED_TEMPLATE_VAR,
            message="Template variable check skipped because the workflow graph has cycles.",
        )
        return result

    # Build topo index map: node_id → position (lower = earlier)
    topo_index = {node_id: idx for idx, node_id in enumerate(topo_order)}

    # Workflow-level variable keys
    workflow_var_keys = set(dsl.variables.keys())

    for node in dsl.nodes:
        if node.is_disabled:
            continue

        # Extract all {{...}} references from this node's params
        all_refs = _extract_all_references(node.params)
        node_topo_pos = topo_index.get(node.id, 9999)

        for ref in all_refs:
            namespace, _ = _parse_ref_namespace(ref)

            # ── Always-valid namespaces ────────────────────────────────────────
            if namespace in ALWAYS_VALID_NAMESPACES:
                continue

            # ── Workflow variables ─────────────────────────────────────────────
            if namespace == "vars":
                _, var_key = _parse_ref_namespace(ref)
                top_key = var_key.split(".")[0]  # "sheet_id" from "sheet_id.subfield"
                if top_key and top_key not in workflow_var_keys:
                    result.add_error(
                        code=ErrorCode.MISSING_WORKFLOW_VAR,
                        node_id=node.id,
                        message=(
                            f"Node '{node.label}' references {{{{vars.{top_key}}}}} "
                            f"but '{top_key}' is not defined in workflow variables. "
                            f"Add it to the workflow's 'variables' section."
                        ),
                        detail={"var_key": top_key, "available": sorted(workflow_var_keys)},
                    )
                continue

            # ── Loop item reference ────────────────────────────────────────────
            if namespace == "item":
                if not _is_inside_loop(node.id, dsl, topo_order):
                    result.add_warning(
                        code=ErrorCode.UNDEFINED_TEMPLATE_VAR,
                        node_id=node.id,
                        message=(
                            f"Node '{node.label}' uses {{{{item...}}}} but is not "
                            f"inside a loop body. '{{{{item...}}}}' is only available "
                            f"within the body of a loop node."
                        ),
                        detail={"ref": ref},
                    )
                continue

            # ── Node output reference: {{other_node_id.field}} ────────────────
            referenced_node_id = namespace

            # Check 1: Referenced node must exist
            if referenced_node_id not in all_node_ids:
                result.add_error(
                    code=ErrorCode.UNDEFINED_TEMPLATE_VAR,
                    node_id=node.id,
                    message=(
                        f"Node '{node.label}' references {{{{{{ {ref} }}}}}}"
                        f" but node '{referenced_node_id}' does not exist in this workflow."
                    ),
                    detail={
                        "ref": ref,
                        "missing_node": referenced_node_id,
                        "available_nodes": sorted(all_node_ids),
                    },
                )
                continue

            # Check 2: Referenced node must be BEFORE current node (topologically)
            ref_topo_pos = topo_index.get(referenced_node_id, 9999)
            if ref_topo_pos >= node_topo_pos:
                result.add_warning(
                    code=ErrorCode.FORWARD_REFERENCE,
                    node_id=node.id,
                    message=(
                        f"Node '{node.label}' references {{{{{{ {ref} }}}}}}"
                        f" but '{referenced_node_id}' may not have executed yet "
                        f"(it appears later in the workflow or on a different branch). "
                        f"This reference may resolve to an empty value at runtime."
                    ),
                    detail={"ref": ref, "referenced_node": referenced_node_id},
                )

    return result
