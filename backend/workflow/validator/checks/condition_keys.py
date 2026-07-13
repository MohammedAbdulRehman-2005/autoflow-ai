"""
AutoFlow AI X — Condition Key Validator  (Bug #1 fix)
=======================================================
Validates that condition expressions in condition_branch nodes only reference
output keys that actually exist in the upstream node's output schema.

The bug: the LLM generates expressions like:
    {{get_emails_1.output.email_list > 0}}

When the actual gmail.get_emails output schema has:
    {"emails": [...], "count": int, "query": str}

So 'email_list' doesn't exist — it should be 'emails' or 'count'.
This validator catches that at save time, before execution.

Detection approach:
  1. Extract all template variable references from the condition string.
     Pattern: {{node_id.output.field_name}}
  2. For each reference, look up the upstream node's output_schema in NodeRegistry.
  3. If the referenced field is not in the schema's top-level properties, raise
     CONDITION_KEY_MISMATCH error.

Limitations (Sprint 1):
  - Only checks top-level output keys (not nested, e.g. emails[0].subject).
  - Only checks references in the pattern {{node_id.output.field}}.
  - Nodes not registered in NodeRegistry are skipped (no false positives).
  - Template expressions that don't match the pattern are ignored.
"""

import re
import logging
from typing import Optional

from backend.workflow.dsl.schema import NodeType, OperationType, WorkflowDSL, WorkflowNodeDSL
from backend.workflow.validator.models import ErrorCode, ValidationResult

logger = logging.getLogger(__name__)

# Matches: {{some_node_id.output.field_name}}
# Captures: (node_id, field_name)
_CONDITION_VAR_RE = re.compile(
    r"\{\{\s*([a-z][a-z0-9_]*)\s*\.\s*output\s*\.\s*([a-z][a-z0-9_]*)\s*",
    re.IGNORECASE,
)


def check_condition_keys(dsl: WorkflowDSL) -> ValidationResult:
    """
    For every condition_branch node, parse the condition expression and verify
    that all referenced output keys actually exist in the upstream node's
    registered output schema.

    Returns a ValidationResult with CONDITION_KEY_MISMATCH errors.
    """
    result = ValidationResult()

    # Lazy import to avoid circular import at module load time.
    from backend.workflow.node_registry import NodeRegistry

    node_map = {n.id: n for n in dsl.nodes}

    for node in dsl.nodes:
        if node.is_disabled:
            continue
        if node.operation != OperationType.condition_branch:
            continue

        condition_str: Optional[str] = node.params.get("condition", "")
        if not condition_str or not isinstance(condition_str, str):
            continue

        # Find all {{node_id.output.field}} references in the condition.
        for match in _CONDITION_VAR_RE.finditer(condition_str):
            ref_node_id = match.group(1)
            ref_field = match.group(2)

            # Does the referenced node exist?
            upstream = node_map.get(ref_node_id)
            if upstream is None:
                # Graph validator will catch UNDEFINED_NODE separately.
                continue

            # Do we have an output schema for the upstream node?
            output_schema = NodeRegistry.get_output_schema(
                upstream.service.value,
                upstream.operation.value,
            )
            if not output_schema:
                # No registered schema for this node type — skip (no false positives).
                continue

            # Is the referenced field in the schema's top-level properties?
            schema_props = output_schema.get("properties", {})
            if not schema_props:
                continue

            if ref_field not in schema_props:
                valid_keys = sorted(schema_props.keys())
                result.add_error(
                    code=ErrorCode.CONDITION_KEY_MISMATCH,
                    node_id=node.id,
                    message=(
                        f"Condition node '{node.label}' references "
                        f"'{{{{ {ref_node_id}.output.{ref_field} }}}}' "
                        f"but '{ref_node_id}' ({upstream.label}) does not have an "
                        f"output key '{ref_field}'. "
                        f"Valid output keys are: {valid_keys}."
                    ),
                    detail={
                        "condition_node":  node.id,
                        "upstream_node":   ref_node_id,
                        "invalid_key":     ref_field,
                        "valid_keys":      valid_keys,
                    },
                )

    return result
