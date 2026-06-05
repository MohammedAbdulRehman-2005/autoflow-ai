"""
AutoFlow AI X — LangGraph State Schema
========================================
Defines the TypedDict state that flows through the LangGraph StateGraph.

State is immutable across nodes — each node returns a partial dict that
LangGraph merges via the Annotated reducers (using operator.add for lists).

State fields:
  context_data     — merged outputs from all completed nodes (node_id → dict)
  run_history      — ordered list of step records (for audit + debugging)
  current_node     — DSL node ID being processed right now
  next_node        — DSL node ID to execute next (set by routing functions)
  error_state      — last error message, None if all good
  trigger_payload  — immutable input from the workflow trigger event
  workflow_meta    — static workflow metadata (name, run_id, etc.)
  agent_scratchpad — per-node scratchpad for multi-step agent reasoning
"""

import operator
from datetime import datetime, timezone
from typing import Annotated, Any, Dict, List, Optional
from typing_extensions import TypedDict


class StepRecord(TypedDict):
    """One entry in run_history — written by each node after execution."""
    node_id:    str
    node_type:  str
    status:     str           # "success" | "failed" | "skipped"
    output:     Dict[str, Any]
    error:      Optional[str]
    started_at: str           # ISO-8601 UTC
    ended_at:   str           # ISO-8601 UTC
    duration_ms: int


class WorkflowState(TypedDict):
    """
    The canonical LangGraph state for AutoFlow AI X workflow execution.

    Reducers:
      - context_data uses dict merge (last write wins per key)
      - run_history uses list append (Annotated[list, operator.add])
      - all other fields use last-write-wins (default)
    """
    # ── Mutable execution state ───────────────────────────────────────────────
    context_data:     Dict[str, Any]      # node_id → output dict (merged across nodes)
    run_history:      Annotated[List[StepRecord], operator.add]   # append-only log
    current_node:     Optional[str]       # DSL node ID currently executing
    next_node:        Optional[str]       # DSL node ID to execute next
    error_state:      Optional[str]       # None = healthy; str = last error

    # ── Immutable inputs ──────────────────────────────────────────────────────
    trigger_payload:  Dict[str, Any]      # data from trigger event
    workflow_meta:    Dict[str, Any]      # { run_id, workflow_id, workflow_name, ... }

    # ── Agent scratchpad (cleared between nodes) ──────────────────────────────
    agent_scratchpad: List[Dict[str, Any]]  # intermediate agent messages/tool calls


def make_initial_state(
    run_id: str,
    workflow_id: str,
    workflow_name: str,
    trigger_payload: Dict[str, Any],
    trigger_node_id: str,
) -> WorkflowState:
    """Build the initial state passed to compiled_graph.ainvoke()."""
    return WorkflowState(
        context_data    = {},
        run_history     = [],
        current_node    = trigger_node_id,
        next_node       = trigger_node_id,
        error_state     = None,
        trigger_payload = trigger_payload,
        workflow_meta   = {
            "run_id":        run_id,
            "workflow_id":   workflow_id,
            "workflow_name": workflow_name,
            "started_at":    datetime.now(timezone.utc).isoformat(),
        },
        agent_scratchpad = [],
    )


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
