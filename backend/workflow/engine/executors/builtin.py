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


class ConditionBranchExecutor(BaseExecutor):
    """
    Evaluates a boolean condition expression.

    Required params:
        condition : A string expression evaluated as truthy/falsy.
                   Supports: comparison against template-resolved values.
                   E.g. the template resolver already resolved {{node.output.count}}
                   so this executor receives the already-resolved string "5" or True.

    Returns:
        output: { "result": true|false, "condition": "..." }

    The runner reads result.output["result"] to determine which edge to follow.
    """

    async def execute(
        self,
        node: WorkflowNodeDSL,
        context: ExecutionContext,
        resolved_params: dict[str, Any],
    ) -> ExecutorResult:
        condition_raw = resolved_params.get("condition", "false")

        # The condition may already be resolved to a bool/int by the context engine
        if isinstance(condition_raw, bool):
            result = condition_raw
        elif isinstance(condition_raw, (int, float)):
            result = bool(condition_raw)
        elif isinstance(condition_raw, str):
            # Evaluate common string representations
            normalized = condition_raw.strip().lower()
            if normalized in ("true", "yes", "1"):
                result = True
            elif normalized in ("false", "no", "0", "none", "null", ""):
                result = False
            else:
                # Try safe Python eval for expressions like "5 > 0" or "len([...]) > 0"
                try:
                    result = bool(eval(condition_raw, {"__builtins__": {}}, {}))
                except Exception:
                    # Non-empty string that isn't a known falsy = truthy
                    result = len(normalized) > 0
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
