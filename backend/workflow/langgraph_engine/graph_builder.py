"""
AutoFlow AI X — DSL → LangGraph Compiler
==========================================
Translates a WorkflowDSL object into a compiled LangGraph StateGraph.

Design:
  1. Detect whether the workflow has any ai_agent nodes.
  2. If yes → build a LangGraph StateGraph (agent runtime).
  3. If no  → return None (caller falls back to simple WorkflowRunner).

Agent node mapping (DSL params.agent_type → LangGraph node function):
  "ai_call_agent"         → ai_call_node
  "lead_scoring_agent"    → lead_scoring_node
  "followup_decision_agent" → follow_up_decision_node
  (anything else)         → generic ReAct agent node

For non-agent DSL nodes (action, condition, delay, transformer):
  → wrap_dsl_node(dsl_node, executor) — runs existing executor inside LangGraph

Graph topology:
  - Trigger node → first non-trigger node
  - Each node's on_success / on_failure edges → added as normal or conditional edges
  - Condition nodes → add_conditional_edges based on output["result"]
  - END node added automatically after terminal nodes
"""

import logging
from typing import Any, Dict, Optional

from langgraph.graph import END, START, StateGraph

from backend.workflow.dsl.schema import NodeType, WorkflowDSL, WorkflowNodeDSL
from backend.workflow.engine.registry import get_executor
from backend.workflow.langgraph_engine.nodes import (
    ai_call_node,
    error_node,
    follow_up_decision_node,
    lead_scoring_node,
    route_after_call_check,
    route_after_lead_scoring,
    success_node,
    wrap_dsl_node,
)
from backend.workflow.langgraph_engine.state import WorkflowState

logger = logging.getLogger(__name__)


# ── Agent type → node function map ───────────────────────────────────────────
AGENT_NODE_MAP = {
    "ai_call_agent":             ai_call_node,
    "lead_scoring_agent":        lead_scoring_node,
    "followup_decision_agent":   follow_up_decision_node,
    "follow_up_decision_agent":  follow_up_decision_node,  # alias
}


def _has_agent_nodes(dsl: WorkflowDSL) -> bool:
    """Return True if any node requires the LangGraph agent runtime."""
    return any(n.type == NodeType.ai_agent for n in dsl.nodes)


def _safe_node_name(node_id: str) -> str:
    """Ensure node names are safe for LangGraph (no dots, starts with letter)."""
    return node_id.replace(".", "_").replace("-", "_")


# ─────────────────────────────────────────────────────────────────────────────
# Main compiler entry point
# ─────────────────────────────────────────────────────────────────────────────

def compile_dsl_to_graph(dsl: WorkflowDSL) -> Optional[Any]:
    """
    Compile a WorkflowDSL into a LangGraph StateGraph.

    Returns:
        A compiled LangGraph graph (call .ainvoke(state) to run it),
        or None if the workflow has no agent nodes (use WorkflowRunner instead).

    Raises:
        ValueError: if the DSL is malformed or references unknown agent types.
    """
    if not _has_agent_nodes(dsl):
        logger.info(
            f"[Compiler] Workflow '{dsl.name}' has no agent nodes — "
            f"using simple executor (no LangGraph overhead)."
        )
        return None

    logger.info(f"[Compiler] Compiling LangGraph graph for workflow '{dsl.name}' "
                f"({len(dsl.nodes)} nodes, {len(dsl.edges)} edges)")

    graph = StateGraph(WorkflowState)

    # ── Register all nodes ────────────────────────────────────────────────────
    node_map: Dict[str, WorkflowNodeDSL] = {n.id: n for n in dsl.nodes}
    registered: set[str] = set()

    for dsl_node in dsl.nodes:
        safe_name = _safe_node_name(dsl_node.id)

        if dsl_node.type == NodeType.trigger:
            # Trigger node = lightweight passthrough in LangGraph
            async def _trigger(state: WorkflowState, _nid=dsl_node.id) -> dict:
                return {"current_node": _nid, "next_node": _nid}
            graph.add_node(safe_name, _trigger)
            registered.add(safe_name)

        elif dsl_node.type == NodeType.ai_agent:
            # Map DSL params.agent_type → concrete agent function
            agent_type = dsl_node.params.get("agent_type", "")
            node_fn    = AGENT_NODE_MAP.get(agent_type)

            if node_fn is None:
                # Unknown agent type → build a generic ReAct agent
                node_fn = _build_generic_agent_node(dsl_node)
                logger.warning(
                    f"[Compiler] Unknown agent_type='{agent_type}' on node '{dsl_node.id}'. "
                    f"Using generic ReAct agent."
                )

            graph.add_node(safe_name, node_fn)
            registered.add(safe_name)

        else:
            # Non-agent node (action, condition, delay, loop, transformer)
            executor = get_executor(dsl_node.service.value, dsl_node.operation.value)
            if executor is None:
                logger.warning(
                    f"[Compiler] No executor for '{dsl_node.service}.{dsl_node.operation}' "
                    f"on node '{dsl_node.id}'. Node will be skipped."
                )
                # Add a no-op pass-through
                async def _noop(state: WorkflowState, _nid=dsl_node.id) -> dict:
                    return {"context_data": {**state.get("context_data", {}), _nid: {"skipped": True}}}
                graph.add_node(safe_name, _noop)
            else:
                graph.add_node(safe_name, wrap_dsl_node(dsl_node, executor))
            registered.add(safe_name)

    # ── Add terminal nodes ────────────────────────────────────────────────────
    graph.add_node("__success__", success_node)
    graph.add_node("__error__",   error_node)

    # ── Wire edges ────────────────────────────────────────────────────────────
    # Find trigger node → START edge
    trigger_node = next(n for n in dsl.nodes if n.type == NodeType.trigger)
    graph.add_edge(START, _safe_node_name(trigger_node.id))

    # Build edge_map: source_id → list of (target_id, label)
    edge_map: Dict[str, list] = {}
    for edge in dsl.edges:
        edge_map.setdefault(edge.source_id, []).append(edge)

    for dsl_node in dsl.nodes:
        safe_src = _safe_node_name(dsl_node.id)

        if dsl_node.type == NodeType.trigger:
            # Connect trigger → first action node (on_success)
            if dsl_node.on_success:
                graph.add_edge(safe_src, _safe_node_name(dsl_node.on_success))
            continue

        if dsl_node.type == NodeType.condition:
            # Conditional edges based on output["result"] boolean
            true_target  = None
            false_target = None

            edges = edge_map.get(dsl_node.id, [])
            for edge in edges:
                if edge.label and edge.label.lower() in ("true", "yes"):
                    true_target = _safe_node_name(edge.target_id)
                elif edge.label and edge.label.lower() in ("false", "no"):
                    false_target = _safe_node_name(edge.target_id)

            # Fallback to on_success / on_failure
            if not true_target and dsl_node.on_success:
                true_target  = _safe_node_name(dsl_node.on_success)
            if not false_target and dsl_node.on_failure:
                false_target = _safe_node_name(dsl_node.on_failure)

            def _condition_router(state: WorkflowState, _t=true_target, _f=false_target) -> str:
                ctx    = state.get("context_data", {})
                result = ctx.get(dsl_node.id, {}).get("result", False)
                if state.get("error_state"):
                    return "__error__"
                return _t if result else (_f or "__success__")

            routes = {}
            if true_target:  routes[true_target]  = true_target
            if false_target: routes[false_target]  = false_target
            routes["__error__"] = "__error__"

            graph.add_conditional_edges(safe_src, _condition_router, routes)
            continue

        # Standard node: on_success → next, on_failure → error_node
        if dsl_node.on_success and _safe_node_name(dsl_node.on_success) in registered:
            graph.add_edge(safe_src, _safe_node_name(dsl_node.on_success))
        else:
            graph.add_edge(safe_src, "__success__")

        # on_failure edges are handled by the node functions returning error_state

    # ── Add terminal edges ────────────────────────────────────────────────────
    graph.add_edge("__success__", END)
    graph.add_edge("__error__",   END)

    compiled = graph.compile()
    logger.info(f"[Compiler] Graph compiled successfully for '{dsl.name}'")
    return compiled


# ─────────────────────────────────────────────────────────────────────────────
# Generic ReAct agent factory (for unknown agent_type values)
# ─────────────────────────────────────────────────────────────────────────────

def _build_generic_agent_node(dsl_node: WorkflowNodeDSL):
    """
    Build a generic ReAct agent node for any DSL ai_agent node that doesn't
    match a named agent type.

    The system prompt and available tools come from the node's params dict:
      params.system_prompt   → agent instructions
      params.tools           → list of tool names from TOOL_MAP
    """
    import time
    from backend.workflow.langgraph_engine.nodes import _run_react_agent, _step_record
    from backend.workflow.langgraph_engine.tools import TOOL_MAP

    node_id      = dsl_node.id
    system_prompt = dsl_node.params.get(
        "system_prompt",
        f"You are an AI agent executing the '{dsl_node.label}' step of an automation workflow. "
        f"Use the provided tools to complete the task and return a JSON result."
    )
    tool_names  = dsl_node.params.get("tools", list(TOOL_MAP.keys()))
    tools       = [TOOL_MAP[t] for t in tool_names if t in TOOL_MAP]
    if not tools:
        tools = list(TOOL_MAP.values())

    async def _generic_agent(state: WorkflowState, _nid=node_id) -> dict:
        import json
        started  = time.monotonic()
        trigger  = state.get("trigger_payload", {})
        ctx      = state.get("context_data", {})
        user_msg = (
            f"Task: {dsl_node.label}\n"
            f"Trigger payload: {json.dumps(trigger, indent=2)}\n"
            f"Context: {json.dumps(ctx, indent=2)}"
        )
        try:
            output, new_scratchpad = await _run_react_agent(
                system_prompt  = system_prompt,
                user_message   = user_msg,
                tools          = tools,
                scratchpad     = state.get("agent_scratchpad", []),
            )
            status, error = "success", None
        except Exception as e:
            output = {"error": str(e)}
            new_scratchpad = state.get("agent_scratchpad", [])
            status, error = "failed", str(e)

        return {
            "context_data":    {**state.get("context_data", {}), _nid: output},
            "agent_scratchpad": new_scratchpad,
            "current_node":    _nid,
            "error_state":     error,
            "run_history":     [_step_record(_nid, "ai_agent", status, output, error, started)],
        }

    _generic_agent.__name__ = f"generic_agent_{node_id}"
    return _generic_agent
