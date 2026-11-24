"""
AutoFlow AI X — Built-in Executors
=====================================
Native AutoFlow operations that don't call external APIs.
These handle conditions, loops, delays, data transformation, and variables.
"""

import asyncio
import logging
from typing import Any

from backend.workflow.dsl.schema import WorkflowNodeDSL
from backend.workflow.engine.context import ExecutionContext
from backend.workflow.engine.executors.base import BaseExecutor, ExecutorResult

logger = logging.getLogger(__name__)


import ast

MAX_EXPR_LENGTH = 500
MAX_AST_NODES = 50
MAX_AST_DEPTH = 8
MAX_COLLECTION_SIZE = 20

SAFE_OPERATORS = {
    ast.Eq: lambda a, b: a == b,
    ast.NotEq: lambda a, b: a != b,
    ast.Lt: lambda a, b: a < b,
    ast.LtE: lambda a, b: a <= b,
    ast.Gt: lambda a, b: a > b,
    ast.GtE: lambda a, b: a >= b,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
    ast.Is: lambda a, b: a is b,
    ast.IsNot: lambda a, b: a is not b,
}

SAFE_UNARY_OPERATORS = {
    ast.Not: lambda a: not a,
    ast.USub: lambda a: -a,
    ast.UAdd: lambda a: +a,
}

SAFE_BOOLEAN_OPERATORS = {
    ast.And: lambda vals: all(vals),
    ast.Or: lambda vals: any(vals),
}


def _calc_ast_depth(node: ast.AST) -> int:
    """Calculate maximum nesting depth of an AST tree."""
    children = list(ast.iter_child_nodes(node))
    if not children:
        return 1
    return 1 + max(_calc_ast_depth(c) for c in children)


def _safe_eval_ast(node: ast.AST) -> Any:
    """Recursively evaluate an AST expression with strict operator whitelisting and resource limits.
    Disallows function calls, attribute access, and arbitrary code execution."""
    if isinstance(node, ast.Expression):
        return _safe_eval_ast(node.body)
    elif isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float, str, bool, type(None))):
            raise ValueError(f"Unsupported constant type: {type(node.value).__name__}")
        return node.value
    elif isinstance(node, ast.List):
        if len(node.elts) > MAX_COLLECTION_SIZE:
            raise ValueError(f"Collection size ({len(node.elts)}) exceeds safety limit of {MAX_COLLECTION_SIZE}.")
        return [_safe_eval_ast(elt) for elt in node.elts]
    elif isinstance(node, ast.Tuple):
        if len(node.elts) > MAX_COLLECTION_SIZE:
            raise ValueError(f"Collection size ({len(node.elts)}) exceeds safety limit of {MAX_COLLECTION_SIZE}.")
        return tuple(_safe_eval_ast(elt) for elt in node.elts)
    elif isinstance(node, ast.Dict):
        if len(node.keys) > MAX_COLLECTION_SIZE:
            raise ValueError(f"Dictionary size ({len(node.keys)}) exceeds safety limit of {MAX_COLLECTION_SIZE}.")
        return {_safe_eval_ast(k): _safe_eval_ast(v) for k, v in zip(node.keys, node.values)}
    elif isinstance(node, ast.Compare):
        left = _safe_eval_ast(node.left)
        for op, comparator in zip(node.ops, node.comparators):
            op_fn = SAFE_OPERATORS.get(type(op))
            if not op_fn:
                raise ValueError(f"Unsupported comparison operator: {type(op).__name__}")
            right = _safe_eval_ast(comparator)
            try:
                if not op_fn(left, right):
                    return False
            except TypeError:
                # Incompatible comparison types evaluate safely to False
                return False
            left = right
        return True
    elif isinstance(node, ast.UnaryOp):
        op_fn = SAFE_UNARY_OPERATORS.get(type(node.op))
        if not op_fn:
            raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
        operand_val = _safe_eval_ast(node.operand)
        try:
            return op_fn(operand_val)
        except TypeError:
            return False
    elif isinstance(node, ast.BoolOp):
        op_fn = SAFE_BOOLEAN_OPERATORS.get(type(node.op))
        if not op_fn:
            raise ValueError(f"Unsupported boolean operator: {type(node.op).__name__}")
        return op_fn([_safe_eval_ast(v) for v in node.values])
    elif isinstance(node, ast.Name):
        lower = node.id.lower()
        if lower in ("true", "yes"):
            return True
        elif lower in ("false", "no"):
            return False
        elif lower in ("none", "null"):
            return None
        raise ValueError(f"Disallowed variable or identifier in condition expression: '{node.id}'")
    else:
        raise ValueError(f"Disallowed expression node type: {type(node).__name__}")


def evaluate_safe_condition(expr: str) -> bool:
    """Safely parse and evaluate a boolean condition expression without Python eval()
    under strict complexity and resource bounds."""
    if not isinstance(expr, str):
        return bool(expr)

    normalized = expr.strip()
    if not normalized:
        return False

    if len(normalized) > MAX_EXPR_LENGTH:
        raise ValueError(
            f"Condition expression exceeds maximum safety length of {MAX_EXPR_LENGTH} characters."
        )

    lower = normalized.lower()
    if lower in ("true", "yes", "1"):
        return True
    elif lower in ("false", "no", "0", "none", "null"):
        return False

    try:
        tree = ast.parse(normalized, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"Malformed condition syntax: {e}") from e

    node_count = sum(1 for _ in ast.walk(tree))
    if node_count > MAX_AST_NODES:
        raise ValueError(
            f"Condition expression complexity exceeds safety limit ({node_count} nodes > {MAX_AST_NODES} maximum)."
        )

    depth = _calc_ast_depth(tree)
    if depth > MAX_AST_DEPTH:
        raise ValueError(
            f"Condition expression nesting depth ({depth}) exceeds safety limit of {MAX_AST_DEPTH}."
        )

    result = _safe_eval_ast(tree)
    return bool(result)


class ConditionBranchExecutor(BaseExecutor):
    """
    Evaluates a boolean condition expression using a safe AST evaluator.
    Python eval() is strictly disallowed and removed.

    Required params:
        condition : A string or boolean expression evaluated as truthy/falsy.
                    Supports: safe comparisons (==, !=, <, <=, >, >=, in, not in, and, or, not).

    Returns:
        output: { "result": true|false, "condition": "..." }
    """

    async def execute(
        self,
        node: WorkflowNodeDSL,
        context: ExecutionContext,
        resolved_params: dict[str, Any],
    ) -> ExecutorResult:
        condition_raw = resolved_params.get("condition", "false")

        if isinstance(condition_raw, bool):
            result = condition_raw
        elif isinstance(condition_raw, (int, float)):
            result = bool(condition_raw)
        elif isinstance(condition_raw, str):
            try:
                result = evaluate_safe_condition(condition_raw)
            except Exception as e:
                logger.error(f"[Condition] Failed safe evaluation of '{condition_raw}': {e}")
                return ExecutorResult.fail(
                    f"Condition expression evaluation failed: {e}",
                    output={"result": False, "condition": str(condition_raw), "error": str(e)},
                )
        else:
            result = bool(condition_raw)

        logger.info(f"[Condition] '{node.label}' evaluated to: {result}")

        return ExecutorResult.ok(output={"result": result, "condition": str(condition_raw)})


class ForEachExecutor(BaseExecutor):
    """
    Signals the runner to begin a loop iteration.
    The actual looping is handled by the WorkflowRunner — this executor
    just validates the items list and returns it.

    Required params:
        items    : List of items to iterate over (template-resolved)
        item_var : Name of the variable (informational, used by runner)

    Returns:
        output: { "items": [...], "count": N }
    """

    async def execute(
        self,
        node: WorkflowNodeDSL,
        context: ExecutionContext,
        resolved_params: dict[str, Any],
    ) -> ExecutorResult:
        items = resolved_params.get("items", [])
        item_var = resolved_params.get("item_var", "item")

        if not isinstance(items, list):
            # If items resolved to a non-list, try to convert
            if items:
                items = [items]
            else:
                items = []

        logger.info(f"[Loop] '{node.label}' will iterate over {len(items)} items as '{item_var}'")

        return ExecutorResult.ok(output={"items": items, "count": len(items), "item_var": item_var})


class WaitExecutor(BaseExecutor):
    """
    Pauses workflow execution for a specified duration.

    Required params:
        duration_seconds : Number of seconds to wait (int or string)

    Note: For production with Celery, this would use Celery's countdown
    instead of asyncio.sleep to avoid blocking a worker thread.
    """

    async def execute(
        self,
        node: WorkflowNodeDSL,
        context: ExecutionContext,
        resolved_params: dict[str, Any],
    ) -> ExecutorResult:
        duration = int(resolved_params.get("duration_seconds", 0))
        duration = max(0, min(duration, 86400))  # Clamp to 0–24h

        logger.info(f"[Delay] '{node.label}' waiting {duration} seconds")
        await asyncio.sleep(duration)

        return ExecutorResult.ok(output={"waited_seconds": duration})


class MapFieldsExecutor(BaseExecutor):
    """
    Transforms data by mapping fields from input to a new output shape.

    Required params:
        mapping : dict of { "output_field": "{{source.field}}" }
                  Template vars are already resolved by the context engine
                  before this executor runs, so values are literal.

    Returns:
        output: { "result": { ...mapped fields... } }
    """

    async def execute(
        self,
        node: WorkflowNodeDSL,
        context: ExecutionContext,
        resolved_params: dict[str, Any],
    ) -> ExecutorResult:
        mapping = resolved_params.get("mapping", {})

        if not isinstance(mapping, dict):
            return ExecutorResult.fail("'mapping' must be a dict for map_fields.")

        logger.info(f"[Transformer] '{node.label}' mapping {len(mapping)} fields")

        return ExecutorResult.ok(output={"result": mapping, "field_count": len(mapping)})


class FilterListExecutor(BaseExecutor):
    """
    Filters a list to only include items matching a condition.

    Required params:
        items     : List to filter (template-resolved)
        condition : Field and value to filter by
                    E.g. { "field": "status", "equals": "active" }

    Returns:
        output: { "items": [...], "count": N, "filtered_count": M }
    """

    async def execute(
        self,
        node: WorkflowNodeDSL,
        context: ExecutionContext,
        resolved_params: dict[str, Any],
    ) -> ExecutorResult:
        items = resolved_params.get("items", [])
        condition = resolved_params.get("condition", {})

        if not isinstance(items, list):
            items = []

        original_count = len(items)
        filtered = items

        if condition and isinstance(items, list) and items:
            field = condition.get("field")
            equals = condition.get("equals")
            if field and equals is not None:
                filtered = [
                    item for item in items
                    if isinstance(item, dict) and str(item.get(field, "")) == str(equals)
                ]

        logger.info(
            f"[Filter] '{node.label}' filtered {original_count} → {len(filtered)} items"
        )

        return ExecutorResult.ok(
            output={"items": filtered, "count": len(filtered), "original_count": original_count}
        )


class SetVariableExecutor(BaseExecutor):
    """
    Sets a workflow-level variable in the context.
    Used for logging, tracking state, or passing values between distant nodes.

    Required params:
        variable : Variable name
        value    : Value to set (template-resolved before reaching this executor)
    """

    async def execute(
        self,
        node: WorkflowNodeDSL,
        context: ExecutionContext,
        resolved_params: dict[str, Any],
    ) -> ExecutorResult:
        variable = resolved_params.get("variable", "")
        value = resolved_params.get("value", "")

        if variable:
            context._workflow_vars[variable] = value
            logger.info(f"[Variable] Set '{variable}' = {repr(value)[:100]}")

        return ExecutorResult.ok(output={"variable": variable, "value": value})


class TriggerExecutor(BaseExecutor):
    """
    Entry point executor. Always succeeds and passes trigger payload downstream.
    The trigger payload is already in the context from initialization.
    """

    async def execute(
        self,
        node: WorkflowNodeDSL,
        context: ExecutionContext,
        resolved_params: dict[str, Any],
    ) -> ExecutorResult:
        logger.info(f"[Trigger] '{node.label}' activated")
        return ExecutorResult.ok(output=context._trigger_payload)
