"""
AutoFlow AI X — LangGraph Agent Node Implementations
======================================================
Each function here is a LangGraph "node" — it receives the WorkflowState,
performs its work (LLM call, tool use, routing decision), and returns a
partial state dict that LangGraph merges back.

Architecture:
  ┌──────────────────────────────────────────────────────────────┐
  │              LangGraph StateGraph                            │
  │                                                              │
  │  trigger_node ──▶ ai_call_node ──▶ lead_scoring_node ──▶   │
  │                     ▼ (tool calls)                           │
  │              follow_up_decision_node ──▶ action_node        │
  └──────────────────────────────────────────────────────────────┘

Node function signature: async def node_fn(state: WorkflowState) -> dict
The returned dict is merged into WorkflowState by LangGraph.

Backward compatibility:
  - Non-agent DSL nodes (action, condition, delay) → wrap_dsl_node()
  - Agent DSL nodes (ai_agent) → use the react_agent_node() factory
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_groq import ChatGroq

from backend.workflow.langgraph_engine.state import StepRecord, WorkflowState, utcnow_iso
from backend.workflow.langgraph_engine.tools import (
    ALL_TOOLS,
    TOOL_MAP,
    append_sheet_tool,
    classify_lead_tool,
    decide_followup_tool,
    send_email_tool,
    send_sms_tool,
)

logger = logging.getLogger(__name__)

_GROQ_API_KEY    = os.environ.get("GROQ_API_KEY", "")
_DEFAULT_MODEL   = "llama-3.3-70b-versatile"
_MAX_TOOL_ROUNDS = 5    # Max ReAct reasoning rounds per agent node


def _make_llm(model: str = _DEFAULT_MODEL, temperature: float = 0.1) -> ChatGroq:
    """Build a ChatGroq LLM instance bound with all tools."""
    return ChatGroq(
        api_key=_GROQ_API_KEY,
        model=model,
        temperature=temperature,
    )


def _step_record(
    node_id: str,
    node_type: str,
    status: str,
    output: Dict[str, Any],
    error: Optional[str],
    started_ms: float,
) -> StepRecord:
    now = utcnow_iso()
    return StepRecord(
        node_id    = node_id,
        node_type  = node_type,
        status     = status,
        output     = output,
        error      = error,
        started_at = now,
        ended_at   = now,
        duration_ms= int((time.monotonic() - started_ms) * 1000),
    )


# ─────────────────────────────────────────────────────────────────────────────
# ReAct agent helper — runs multi-step tool-use loop
# ─────────────────────────────────────────────────────────────────────────────

async def _run_react_agent(
    system_prompt: str,
    user_message:  str,
    tools:         list,
    scratchpad:    List[Dict[str, Any]],
) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Run a ReAct (Reason + Act) agent loop.

    Returns: (final_output_dict, updated_scratchpad)

    The loop:
      1. LLM reasons → decides whether to call a tool
      2. If tool call: execute tool, feed result back as ToolMessage
      3. Repeat up to _MAX_TOOL_ROUNDS times
      4. Final LLM response is parsed as JSON output
    """
    llm = _make_llm().bind_tools(tools)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ]

    # Replay any existing scratchpad messages
    for msg_dict in scratchpad:
        role = msg_dict.get("role")
        if role == "ai":
            messages.append(AIMessage(content=msg_dict.get("content", "")))
        elif role == "tool":
            messages.append(ToolMessage(
                content=msg_dict.get("content", ""),
                tool_call_id=msg_dict.get("tool_call_id", ""),
            ))

    final_output: Dict[str, Any] = {}
    new_scratchpad: List[Dict[str, Any]] = list(scratchpad)

    for _round in range(_MAX_TOOL_ROUNDS):
        response = await llm.ainvoke(messages)

        # Record AI response in scratchpad
        new_scratchpad.append({"role": "ai", "content": str(response.content)})
        messages.append(response)

        # If no tool calls → agent has finished reasoning
        if not response.tool_calls:
            # Try to parse final content as JSON output
            content = response.content or ""
            try:
                start = content.find("{")
                end   = content.rfind("}") + 1
                if start >= 0:
                    final_output = json.loads(content[start:end])
                else:
                    final_output = {"result": content}
            except Exception:
                final_output = {"result": content}
            break

        # Execute each tool call
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_fn   = TOOL_MAP.get(tool_name)

            if tool_fn is None:
                tool_result = {"error": f"Tool '{tool_name}' not found."}
            else:
                try:
                    tool_result = await tool_fn.ainvoke(tool_args)
                except Exception as e:
                    tool_result = {"error": str(e)}

            result_str = json.dumps(tool_result)
            tool_msg = ToolMessage(content=result_str, tool_call_id=tool_call["id"])
            messages.append(tool_msg)
            new_scratchpad.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "tool_name": tool_name,
                "content": result_str,
            })

    return final_output, new_scratchpad


# ─────────────────────────────────────────────────────────────────────────────
# NODE 1: AI Call Decision Agent
# Decides whether to escalate to a phone call alert
# ─────────────────────────────────────────────────────────────────────────────

async def ai_call_node(state: WorkflowState) -> dict:
    """
    AI Call Decision Agent node.

    Examines the current context and decides if an immediate phone call
    alert is warranted. Can use send_sms_tool to dispatch a call request.

    DSL node type: ai_agent, operation: llm_classify
    Maps to operation: "should_call_agent"
    """
    started = time.monotonic()
    node_id = "ai_call_node"

    system_prompt = """You are an urgent-response decision agent for a real estate CRM.
Your job: decide if the current context requires an immediate phone call alert.

If a call is warranted:
1. Use send_sms_tool to send an alert SMS to the agent's phone.
2. Return a JSON decision.

Decision JSON format:
{
  "call_required": true | false,
  "urgency_level": "critical" | "high" | "normal" | "low",
  "reason": "<why call is/isn't needed>",
  "sms_sent": true | false,
  "recipient": "<phone or empty>"
}"""

    # Build user message from current context
    trigger = state.get("trigger_payload", {})
    ctx     = state.get("context_data", {})
    user_msg = f"""Current trigger payload: {json.dumps(trigger, indent=2)}
Context so far: {json.dumps(ctx, indent=2)}
Workflow: {state.get('workflow_meta', {}).get('workflow_name', 'unknown')}"""

    try:
        output, new_scratchpad = await _run_react_agent(
            system_prompt=system_prompt,
            user_message=user_msg,
            tools=[send_sms_tool],
            scratchpad=state.get("agent_scratchpad", []),
        )
        status = "success"
        error  = None
    except Exception as e:
        output = {"call_required": False, "urgency_level": "low", "reason": str(e)}
        new_scratchpad = state.get("agent_scratchpad", [])
        status = "failed"
        error  = str(e)
        logger.error(f"[ai_call_node] Failed: {e}", exc_info=True)

    return {
        "context_data": {**state.get("context_data", {}), node_id: output},
        "agent_scratchpad": new_scratchpad,
        "current_node": node_id,
        "error_state": error,
        "run_history": [_step_record(node_id, "ai_agent", status, output, error, started)],
    }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 2: Lead Scoring Agent
# Classifies a real-estate lead with AI reasoning
# ─────────────────────────────────────────────────────────────────────────────

async def lead_scoring_node(state: WorkflowState) -> dict:
    """
    Real-estate lead scoring agent.

    Uses classify_lead_tool to score and tier the lead, then optionally
    appends results to a Google Sheet via append_sheet_tool.

    DSL node type: ai_agent, operation: llm_classify → "lead_scoring_agent"
    """
    started = time.monotonic()
    node_id = "lead_scoring_node"

    system_prompt = """You are a real estate lead intelligence agent.

Step 1: Use classify_lead_tool to score the lead from the context.
Step 2: If score >= 70 (hot lead), use append_sheet_tool to log it.
Step 3: Return a final JSON summary.

Final JSON format:
{
  "score": <0-100>,
  "tier": "hot" | "warm" | "cold",
  "logged_to_sheet": true | false,
  "recommended_action": "<what should happen next>",
  "reasoning": "<brief explanation>"
}"""

    trigger = state.get("trigger_payload", {})
    ctx     = state.get("context_data", {})
    user_msg = f"""Lead data from trigger: {json.dumps(trigger, indent=2)}
Additional context: {json.dumps(ctx, indent=2)}"""

    try:
        output, new_scratchpad = await _run_react_agent(
            system_prompt=system_prompt,
            user_message=user_msg,
            tools=[classify_lead_tool, append_sheet_tool],
            scratchpad=state.get("agent_scratchpad", []),
        )
        status = "success"
        error  = None
    except Exception as e:
        output = {"score": 0, "tier": "cold", "reasoning": str(e)}
        new_scratchpad = state.get("agent_scratchpad", [])
        status = "failed"
        error  = str(e)
        logger.error(f"[lead_scoring_node] Failed: {e}", exc_info=True)

    return {
        "context_data": {**state.get("context_data", {}), node_id: output},
        "agent_scratchpad": new_scratchpad,
        "current_node": node_id,
        "error_state": error,
        "run_history": [_step_record(node_id, "ai_agent", status, output, error, started)],
    }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 3: Follow-Up Decision Agent
# Decides what follow-up to take and executes it
# ─────────────────────────────────────────────────────────────────────────────

async def follow_up_decision_node(state: WorkflowState) -> dict:
    """
    Follow-up decision + execution agent.

    Reads upstream scoring results and decides which follow-up to take:
      - Hot lead → immediate email + SMS
      - Warm lead → email within 24h
      - Cold lead → no action or newsletter enrollment

    DSL node type: ai_agent, operation: llm_generate → "followup_decision_agent"
    """
    started = time.monotonic()
    node_id = "follow_up_decision_node"

    # Extract lead scoring results from upstream context
    ctx = state.get("context_data", {})
    lead_result = ctx.get("lead_scoring_node", {})
    tier  = lead_result.get("tier", "unknown")
    score = lead_result.get("score", 0)

    system_prompt = f"""You are a follow-up orchestration agent.
The lead has been scored: tier={tier}, score={score}.

Rules:
- Hot (score >= 70): Use send_email_tool AND send_sms_tool immediately.
- Warm (score 40-69): Use send_email_tool only.
- Cold (score < 40): Use decide_followup_tool to evaluate, then act accordingly.

Return final JSON:
{{
  "actions_taken": ["email", "sms"] or [],
  "follow_up_scheduled": true | false,
  "next_contact_channel": "email" | "sms" | "call" | "none",
  "summary": "<what happened>"
}}"""

    trigger  = state.get("trigger_payload", {})
    user_msg = f"""Trigger data: {json.dumps(trigger, indent=2)}
Full context: {json.dumps(ctx, indent=2)}"""

    try:
        output, new_scratchpad = await _run_react_agent(
            system_prompt=system_prompt,
            user_message=user_msg,
            tools=[send_email_tool, send_sms_tool, decide_followup_tool],
            scratchpad=state.get("agent_scratchpad", []),
        )
        status = "success"
        error  = None
    except Exception as e:
        output = {"actions_taken": [], "summary": str(e)}
        new_scratchpad = state.get("agent_scratchpad", [])
        status = "failed"
        error  = str(e)
        logger.error(f"[follow_up_decision_node] Failed: {e}", exc_info=True)

    return {
        "context_data": {**state.get("context_data", {}), node_id: output},
        "agent_scratchpad": new_scratchpad,
        "current_node": node_id,
        "error_state": error,
        "run_history": [_step_record(node_id, "ai_agent", status, output, error, started)],
    }


# ─────────────────────────────────────────────────────────────────────────────
# ROUTER: Conditional edge functions
# ─────────────────────────────────────────────────────────────────────────────

def route_after_lead_scoring(state: WorkflowState) -> str:
    """
    Conditional edge: after lead_scoring_node, route to the right next node.
    Returns the LangGraph node name to go to next.
    """
    ctx   = state.get("context_data", {})
    score = ctx.get("lead_scoring_node", {}).get("score", 0)

    if state.get("error_state"):
        return "error_node"
    if score >= 70:
        # Hot lead: skip call check, go straight to follow-up
        return "follow_up_decision_node"
    elif score >= 40:
        # Warm lead: check for call, then follow-up
        return "ai_call_node"
    else:
        # Cold lead: only follow-up evaluation
        return "follow_up_decision_node"


def route_after_call_check(state: WorkflowState) -> str:
    """Conditional edge: after ai_call_node."""
    if state.get("error_state"):
        return "error_node"
    return "follow_up_decision_node"


# ─────────────────────────────────────────────────────────────────────────────
# Terminal nodes
# ─────────────────────────────────────────────────────────────────────────────

async def success_node(state: WorkflowState) -> dict:
    """Terminal node — marks the run as complete."""
    return {
        "current_node": "__success__",
        "next_node": None,
        "run_history": [_step_record(
            "__success__", "terminal", "success",
            {"message": "Workflow completed successfully."}, None, time.monotonic()
        )],
    }


async def error_node(state: WorkflowState) -> dict:
    """Terminal node — captures the final error state."""
    err = state.get("error_state", "Unknown error")
    logger.error(f"[LangGraph] Workflow terminated in error_node: {err}")
    return {
        "current_node": "__error__",
        "next_node": None,
        "run_history": [_step_record(
            "__error__", "terminal", "failed",
            {"error": err}, err, time.monotonic()
        )],
    }


# ─────────────────────────────────────────────────────────────────────────────
# DSL NODE WRAPPER — for non-agent nodes (backward compat)
# ─────────────────────────────────────────────────────────────────────────────

def wrap_dsl_node(dsl_node, executor):
    """
    Wraps a simple DSL node + executor pair into a LangGraph node function.
    Used for non-agent nodes (action, condition, delay, transformer).

    Returns an async function with the correct LangGraph signature.
    """
    from backend.workflow.engine.context import ExecutionContext
    import uuid

    node_id   = dsl_node.id
    node_type = dsl_node.type.value

    async def _node_fn(state: WorkflowState) -> dict:
        started = time.monotonic()
        meta    = state.get("workflow_meta", {})
        run_id  = uuid.UUID(meta.get("run_id", str(uuid.uuid4())))

        # Build a minimal ExecutionContext from current state
        ctx = ExecutionContext(
            run_id           = run_id,
            trigger_payload  = state.get("trigger_payload", {}),
            workflow_variables = {},
        )
        for _node_id, _output in state.get("context_data", {}).items():
            ctx.set_node_output(_node_id, _output)

        resolved_params = ctx.resolve_params(dsl_node.params)

        try:
            result = await executor.execute(dsl_node, ctx, resolved_params)
            output = result.output or {}
            status = "success" if result.success else "failed"
            error  = result.error
        except Exception as e:
            output = {}
            status = "failed"
            error  = str(e)
            logger.error(f"[wrap_dsl_node:{node_id}] {e}", exc_info=True)

        return {
            "context_data": {**state.get("context_data", {}), node_id: output},
            "current_node": node_id,
            "error_state": error if status == "failed" else state.get("error_state"),
            "run_history": [_step_record(node_id, node_type, status, output, error, started)],
        }

    _node_fn.__name__ = f"dsl_node_{node_id}"
    return _node_fn
