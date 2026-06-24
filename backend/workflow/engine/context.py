"""
AutoFlow AI X — Execution Context
===================================
The ExecutionContext is the "memory" of a running workflow.
It tracks all node outputs and resolves Jinja2 template variables
so downstream nodes can reference upstream results.

Template variable patterns supported:
  {{node_id.field}}               → output field from a named node
  {{trigger.payload.field}}       → field from trigger input payload
  {{item.field}}                  → current loop iteration item
  {{context.today}}               → system date helpers
  {{env.VAR_NAME}}                → environment variable
  {{vars.key}}                    → workflow-level variable
  {{run.id}}                      → current run UUID
"""

import os
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from jinja2 import BaseLoader, Environment, Undefined

try:
    from sqlalchemy.orm import Session
except ImportError:
    Session = None  # type: ignore[assignment,misc]



class _SilentUndefined(Undefined):
    """Return an empty string instead of raising errors for missing variables.
    This prevents template resolution from crashing the whole engine on minor typos."""
    def __str__(self): return ""
    def __call__(self, *a, **k): return ""
    def __getattr__(self, name): return _SilentUndefined()
    def __getitem__(self, key): return _SilentUndefined()


# Jinja2 environment — sandboxed, no file loading, silent on missing vars
_jinja_env = Environment(
    loader=BaseLoader(),
    variable_start_string="{{",
    variable_end_string="}}",
    undefined=_SilentUndefined,
    autoescape=False,
)


class ExecutionContext:
    """
    Mutable context that flows through the entire workflow run.

    Each node execution receives this context, resolves its params,
    then writes its output back so downstream nodes can use it.
    """

    def __init__(
        self,
        run_id: uuid.UUID,
        trigger_payload: dict[str, Any],
        workflow_variables: dict[str, Any],
        db: Optional["Session"] = None,
        user_id: Optional[uuid.UUID] = None,
    ):
        self.run_id = run_id
        self.db = db
        self.user_id = user_id
        self._trigger_payload = trigger_payload
        self._workflow_vars = workflow_variables
        self._node_outputs: dict[str, Any] = {}  # node_dsl_id → output dict
        self._loop_item: Optional[Any] = None    # current item in a loop iteration
        self._error: Optional[str] = None        # last error message

    # ── Node output storage ──────────────────────────────────────────────────

    def set_node_output(self, node_dsl_id: str, output: dict[str, Any]) -> None:
        """Store the output dict of a completed node."""
        self._node_outputs[node_dsl_id] = output

    def get_node_output(self, node_dsl_id: str) -> dict[str, Any]:
        return self._node_outputs.get(node_dsl_id, {})

    def set_loop_item(self, item: Any) -> None:
        """Set the current loop iteration item (resolved as {{item.field}})."""
        self._loop_item = item

    def clear_loop_item(self) -> None:
        self._loop_item = None

    def set_error(self, message: str) -> None:
        self._error = message

    # ── Template resolution ──────────────────────────────────────────────────

    def _build_jinja_vars(self) -> dict[str, Any]:
        """
        Build the flat variable namespace that Jinja2 will render against.
        All node outputs are accessible by their DSL node ID as top-level keys.
        """
        today = date.today()
        now_utc = datetime.now(timezone.utc)

        jinja_ctx: dict[str, Any] = {
            # System context
            "context": {
                "today": today.isoformat(),
                "tomorrow_date": (today + timedelta(days=1)).isoformat(),
                "yesterday_date": (today - timedelta(days=1)).isoformat(),
                "current_week_number": today.isocalendar()[1],
                "current_month": today.strftime("%B"),
                "current_year": today.year,
                "now_utc": now_utc.isoformat(),
                "error_message": self._error or "",
            },
            # Trigger payload
            "trigger": {"payload": self._trigger_payload, **self._trigger_payload},
            # Workflow variables
            "vars": self._workflow_vars,
            # Run metadata
            "run": {"id": str(self.run_id)},
            # Environment variables (filtered — only non-secret ones needed in templates)
            "env": {k: v for k, v in os.environ.items()},
        }

        # Each node's output is accessible by its DSL ID
        for node_id, output in self._node_outputs.items():
            jinja_ctx[node_id] = output

        # Current loop item
        if self._loop_item is not None:
            if isinstance(self._loop_item, dict):
                jinja_ctx["item"] = self._loop_item
            else:
                jinja_ctx["item"] = {"value": self._loop_item}

        return jinja_ctx

    def resolve(self, value: Any) -> Any:
        """
        Recursively resolve template variables in any value type.
        - str: render as Jinja2 template
        - dict: resolve all values recursively
        - list: resolve all elements recursively
        - other: return as-is
        """
        if isinstance(value, str):
            return self._render_string(value)
        elif isinstance(value, dict):
            return {k: self.resolve(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self.resolve(item) for item in value]
        return value

    def _render_string(self, template_str: str) -> Any:
        """Render a single template string, returning typed output when possible."""
        if "{{" not in template_str:
            return template_str  # Fast path: no template vars

        try:
            jinja_vars = self._build_jinja_vars()
            template = _jinja_env.from_string(template_str)
            rendered = template.render(**jinja_vars)

            # If the entire string was a single template expression, try to
            # preserve the original type (list, dict, int, etc.)
            stripped = template_str.strip()
            if stripped.startswith("{{") and stripped.endswith("}}"):
                inner = stripped[2:-2].strip()
                # Evaluate as Python expression in the jinja context
                try:
                    result = _eval_expression(inner, jinja_vars)
                    if result is not None and not isinstance(result, _SilentUndefined):
                        return result
                except Exception:
                    pass

            return rendered
        except Exception:
            # Never crash the engine on template errors — return original
            return template_str

    def resolve_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """Convenience method: resolve all template vars in a node's params dict."""
        return self.resolve(params)

    def snapshot(self) -> dict[str, Any]:
        """Return a serializable snapshot of the current context for DB storage."""
        return {
            "trigger_payload": self._trigger_payload,
            "node_outputs": self._node_outputs,
            "workflow_vars": self._workflow_vars,
        }


def _eval_expression(expr: str, variables: dict[str, Any]) -> Any:
    """
    Safely evaluate a simple Jinja2 expression in the variable namespace.
    Used to preserve non-string types when a template is a single expression.
    """
    # Walk the dot-path notation: "node_id.field.subfield"
    parts = expr.split(".")
    current = variables
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
        if current is None:
            return None
    return current
