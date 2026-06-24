"""
AutoFlow AI X — Schema Validation Check
=========================================
Validates that each node has all required params for its operation.
This runs BEFORE calling any external APIs, catching config mistakes early.

Required param definitions per operation:
  - "required" : params that must be present and non-empty
  - "allowed"  : all known params for this operation (used to detect unknown params)
  - "types"    : expected Python types for specific params (optional)

Terminal node rule (shared with graph.py):
  A node is considered an intentional terminal/sink when BOTH on_success and
  on_failure are None.  We use the same is_terminal_node() helper in both files
  so the definition never diverges.
"""

from typing import Any

from backend.workflow.dsl.schema import NodeType, OperationType, WorkflowDSL, WorkflowNodeDSL
from backend.workflow.validator.models import ErrorCode, ValidationResult


# ─────────────────────────────────────────────────────────────────────────────
# SHARED TERMINAL-NODE PREDICATE
# A node is a deliberate endpoint when it has nowhere to go on either path.
# Import this in graph.py to keep the two files using the same definition.
# ─────────────────────────────────────────────────────────────────────────────

def is_terminal_node(node: WorkflowNodeDSL) -> bool:
    """Return True when a node is an intentional terminal / error-sink step."""
    return node.on_success is None and node.on_failure is None

# ─────────────────────────────────────────────────────────────────────────────
# OPERATION → REQUIRED PARAMS MAP
# Fields that must be present and non-empty for an operation to be valid.
# A field with value `None`, `""`, or `[]` is treated as missing.
# ─────────────────────────────────────────────────────────────────────────────

OPERATION_REQUIRED_PARAMS: dict[str, dict] = {
    # Gmail
    OperationType.send_email.value: {
        "required": ["to", "subject", "body"],
        "allowed":  ["to", "subject", "body", "cc", "bcc", "reply_to"],
    },
    OperationType.get_emails.value: {
        "required": ["query"],
        "allowed":  ["query", "max_results"],
        # query: Gmail search syntax, e.g. 'in:inbox is:unread'
    },
    OperationType.create_draft.value: {
        "required": ["to", "subject", "body"],
        "allowed":  ["to", "subject", "body", "cc", "bcc"],
    },

    # Google Sheets
    OperationType.read_rows.value: {
        "required": ["spreadsheet_id", "range"],
        "allowed":  ["spreadsheet_id", "range", "filter"],
    },
    OperationType.append_row.value: {
        "required": ["spreadsheet_id", "range", "row"],
        "allowed":  ["spreadsheet_id", "range", "row"],
    },
    OperationType.update_row.value: {
        "required": ["spreadsheet_id", "range"],
        "allowed":  ["spreadsheet_id", "range", "row", "condition"],
    },
    OperationType.find_row.value: {
        "required": ["spreadsheet_id", "range"],
        "allowed":  ["spreadsheet_id", "range", "filter"],
    },

    # HTTP
    OperationType.http_request.value: {
        "required": ["url", "method"],
        "allowed":  ["url", "method", "headers", "body", "timeout_seconds"],
    },

    # AI
    OperationType.llm_generate.value: {
        "required": ["user_prompt"],
        "allowed":  ["model", "system_prompt", "user_prompt", "max_tokens", "temperature"],
    },
    OperationType.llm_classify.value: {
        "required": ["text", "labels"],
        "allowed":  ["model", "text", "labels"],
    },
    OperationType.llm_extract.value: {
        "required": ["text", "fields"],
        "allowed":  ["model", "text", "fields"],
    },

    # Slack
    OperationType.post_message.value: {
        "required": ["channel", "text"],
        "allowed":  ["channel", "text", "blocks", "username", "icon_emoji"],
    },

    # Built-in
    OperationType.condition_branch.value: {
        "required": ["condition"],
        "allowed":  ["condition"],
    },
    OperationType.for_each.value: {
        "required": ["items"],
        "allowed":  ["items", "item_var"],
    },
    OperationType.wait.value: {
        "required": ["duration_seconds"],
        "allowed":  ["duration_seconds"],
    },
    OperationType.map_fields.value: {
        "required": ["mapping"],
        "allowed":  ["mapping"],
    },
    OperationType.filter_list.value: {
        "required": ["items"],
        "allowed":  ["items", "condition"],
    },
    OperationType.set_variable.value: {
        "required": ["variable", "value"],
        "allowed":  ["variable", "value"],
    },

    # Triggers — params are optional (validated at trigger-config level)
    OperationType.cron.value:          {"required": [], "allowed": ["cron", "timezone"]},
    OperationType.webhook_listen.value: {"required": [], "allowed": ["path", "secret", "method"]},
    OperationType.manual_trigger.value: {"required": [], "allowed": ["description"]},
}

# Params that must be lists (not strings or dicts) when present
LIST_PARAMS = {
    OperationType.llm_classify.value:  ["labels"],
    OperationType.llm_extract.value:   ["fields"],
}

# Params that must be dicts when present
DICT_PARAMS = {
    OperationType.map_fields.value:    ["mapping"],
    OperationType.append_row.value:    ["row"],
    OperationType.filter_list.value:   ["condition"],
}


def _is_present(value: Any) -> bool:
    """
    A param is considered "present" if it's non-None, non-empty string,
    and non-empty collection. Template variables ({{...}}) count as present.
    """
    if value is None:
        return False
    if isinstance(value, str):
        return len(value.strip()) > 0
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return True


def check_schema(dsl: WorkflowDSL) -> ValidationResult:
    """
    Validates that every node has all required params for its operation.
    Also checks param types (list vs dict) where applicable.
    """
    result = ValidationResult()

    # ── 1. Trigger cron expression ────────────────────────────────────────────
    if dsl.trigger.type.value == "schedule":
        config = dsl.trigger.config
        cron = getattr(config, "cron", None)
        if cron:
            parts = cron.strip().split()
            if len(parts) not in (5, 6):
                result.add_error(
                    code=ErrorCode.INVALID_CRON_EXPRESSION,
                    message=f"Invalid cron expression '{cron}': must have 5 or 6 space-separated fields.",
                    detail={"cron": cron},
                )
            else:
                # Validate basic cron field constraints
                _validate_cron_fields(parts, result)

    # ── 2. Per-node param checks ──────────────────────────────────────────────
    for node in dsl.nodes:
        if node.is_disabled:
            continue  # Skip disabled nodes

        op_key = node.operation.value
        spec = OPERATION_REQUIRED_PARAMS.get(op_key, {})
        required_fields: list[str] = spec.get("required", [])

        for field_name in required_fields:
            value = node.params.get(field_name)
            if not _is_present(value):
                result.add_error(
                    code=ErrorCode.MISSING_REQUIRED_PARAM,
                    node_id=node.id,
                    message=(
                        f"Node '{node.label}' is missing required param '{field_name}' "
                        f"for operation '{op_key}'."
                    ),
                    detail={"param": field_name, "operation": op_key},
                )

        # ── Type checks ───────────────────────────────────────────────────────
        list_fields = LIST_PARAMS.get(op_key, [])
        for lf in list_fields:
            val = node.params.get(lf)
            if val is not None and not isinstance(val, (list, str)):
                # Allow strings (template vars resolve to lists)
                result.add_error(
                    code=ErrorCode.INVALID_PARAM_TYPE,
                    node_id=node.id,
                    message=f"Param '{lf}' on node '{node.label}' must be a list.",
                    detail={"param": lf, "got": type(val).__name__},
                )

        dict_fields = DICT_PARAMS.get(op_key, [])
        for df in dict_fields:
            val = node.params.get(df)
            if val is not None and not isinstance(val, (dict, str)):
                result.add_error(
                    code=ErrorCode.INVALID_PARAM_TYPE,
                    node_id=node.id,
                    message=f"Param '{df}' on node '{node.label}' must be a dict.",
                    detail={"param": df, "got": type(val).__name__},
                )

        # ── Unknown-param detection ───────────────────────────────────────────
        # If the spec defines an 'allowed' set, warn about params not in it.
        # This catches LLM param pollution (e.g. sending label/unread_only
        # alongside the correct query for get_emails) that won't error at
        # validation time but will confuse the runtime executor.
        allowed_fields: list[str] = spec.get("allowed", [])
        if allowed_fields:  # Only check when spec explicitly defines allowed params
            for param_key in node.params:
                if param_key not in allowed_fields:
                    result.add_warning(
                        code=ErrorCode.INVALID_PARAM_TYPE,
                        node_id=node.id,
                        message=(
                            f"Node '{node.label}' has unknown param '{param_key}' "
                            f"for operation '{op_key}'. "
                            f"Known params: {allowed_fields}."
                        ),
                        detail={"param": param_key, "allowed": allowed_fields},
                    )

        # ── Condition node must have on_success + on_failure ──────────────────
        if node.type == NodeType.condition:
            edges_from_node = [e for e in dsl.edges if e.source_id == node.id]
            has_true_edge = any(
                e.label and e.label.lower() in ("true", "yes") for e in edges_from_node
            ) or node.on_success
            has_false_edge = any(
                e.label and e.label.lower() in ("false", "no") for e in edges_from_node
            ) or node.on_failure

            if not has_true_edge:
                result.add_warning(
                    code=ErrorCode.MISSING_CONDITION_BRANCH,
                    node_id=node.id,
                    message=f"Condition node '{node.label}' has no 'true' branch — truthy results will dead-end.",
                )
            if not has_false_edge:
                result.add_warning(
                    code=ErrorCode.MISSING_CONDITION_BRANCH,
                    node_id=node.id,
                    message=f"Condition node '{node.label}' has no 'false' branch — falsy results will dead-end.",
                )

        # ── Mid-chain action nodes without on_failure get a warning ─────────────
        # We only warn when the node has an on_success target (i.e. it sits in the
        # middle of a chain) but is missing an on_failure handler.  Intentional
        # terminal / error-sink nodes (on_success=None AND on_failure=None) are
        # deliberate dead-ends and must not generate noise.
        if (
            node.type == NodeType.action
            and not node.is_disabled
            and node.on_success is not None   # mid-chain: has a happy path
            and node.on_failure is None        # but no error path
        ):
            result.add_warning(
                code=ErrorCode.MISSING_FAILURE_HANDLER,
                node_id=node.id,
                message=(
                    f"Action node '{node.label}' has no on_failure handler. "
                    f"A failure here will stop the entire workflow run."
                ),
            )

    return result


def _validate_cron_fields(parts: list[str], result: ValidationResult) -> None:
    """Basic sanity check for cron field values (not exhaustive)."""
    field_names = ["minute", "hour", "day", "month", "weekday"]
    field_ranges = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 7)]

    for i, (name, (lo, hi)) in enumerate(zip(field_names, field_ranges)):
        val = parts[i]
        if val in ("*", "?"):
            continue
        # Allow common shorthand: */5, 1-5, 1,2,3
        if "/" in val or "-" in val or "," in val:
            continue
        # Check if it's a plain number in range
        try:
            n = int(val)
            if not (lo <= n <= hi):
                result.add_error(
                    code=ErrorCode.INVALID_CRON_EXPRESSION,
                    message=f"Cron field '{name}' value {n} is out of range [{lo}-{hi}].",
                    detail={"field": name, "value": val},
                )
        except ValueError:
            # Named values like MON, JAN — skip range check
            pass
