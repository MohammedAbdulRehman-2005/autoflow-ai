"""
AutoFlow AI X — Workflow Planner Service
=========================================
The engine that converts a user's structured intent into a validated, saved workflow.

Pipeline:
  1. Build the Groq prompt with full DSL spec + examples
  2. Call Groq API (llama-3.3-70b-versatile — fast and accurate)
  3. Extract JSON from the response (handle markdown wrappers)
  4. Parse with Pydantic WorkflowDSL (structural validation)
  5. Run graph validation (cycle detection, reachability, condition integrity)
  6. If validation fails → retry with error feedback (up to MAX_RETRIES times)
  7. Save workflow + nodes + edges to PostgreSQL
  8. Return full response with graph stats

This is NOT a thin LLM wrapper. Each step has real logic.
"""

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from groq import Groq
from pydantic import ValidationError
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.database.models import (
    Workflow,
    WorkflowEdge,
    WorkflowNode,
    WorkflowStatus,
)
from backend.workflow.dsl.schema import NodeType, WorkflowDSL
from backend.workflow.dsl.validator import ValidationResult, validate_workflow_graph
from backend.workflow.planner.prompt import build_retry_prompt, build_system_prompt
from backend.workflow.planner.schemas import (
    GraphStats,
    IntentDetails,
    PlanWorkflowResponse,
)
from backend.workflow.validator.checks.schema import check_schema


logger = logging.getLogger(__name__)
settings = get_settings()

MAX_RETRIES = 2          # Max additional attempts after the first failure
GROQ_MODEL  = "llama-3.3-70b-versatile"
GROQ_MAX_TOKENS = 4096
GROQ_TEMPERATURE = 0.2   # Low temperature = more deterministic, fewer hallucinations


# ─────────────────────────────────────────────────────────────────────────────
# JSON EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

def _extract_json(raw: str) -> str:
    """
    Extract a JSON object from LLM output that may be wrapped in markdown
    code blocks or have leading/trailing text.

    Tries, in order:
      1. Strip ```json ... ``` blocks
      2. Find first '{' to last '}' (greedy JSON extraction)
      3. Return raw stripped string as fallback
    """
    # Strip markdown code fences
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()

    # Greedy JSON object extraction
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        return raw[start : end + 1].strip()

    return raw.strip()


# ─────────────────────────────────────────────────────────────────────────────
# GRAPH STATS
# ─────────────────────────────────────────────────────────────────────────────

def _compute_graph_stats(dsl: WorkflowDSL) -> GraphStats:
    """Compute summary statistics from the validated DSL for the API response."""
    trigger_node = next((n for n in dsl.nodes if n.type == NodeType.trigger), None)
    services_used = list({n.service.value for n in dsl.nodes if n.type != NodeType.trigger})

    return GraphStats(
        node_count=len(dsl.nodes),
        edge_count=len(dsl.edges),
        trigger_type=dsl.trigger.type.value,
        services_used=sorted(services_used),
        has_condition=any(n.type == NodeType.condition for n in dsl.nodes),
        has_loop=any(n.type == NodeType.loop for n in dsl.nodes),
        has_ai_agent=any(n.type == NodeType.ai_agent for n in dsl.nodes),
    )


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE PERSISTENCE
# ─────────────────────────────────────────────────────────────────────────────

def _save_workflow_to_db(
    dsl: WorkflowDSL,
    workflow_name: str,
    original_prompt: str,
    user_id: uuid.UUID,
    db: Session,
) -> Workflow:
    """
    Persist the validated DSL to PostgreSQL.
    Creates:
      - 1 Workflow record (with full DSL JSON stored in ai_context_json)
      - N WorkflowNode records
      - M WorkflowEdge records

    All within a single transaction so partial failures don't corrupt the DB.
    """
    # Determine cron expression if this is a schedule trigger
    cron_expr: Optional[str] = None
    timezone_str = "UTC"
    if dsl.trigger.type.value == "schedule":
        config = dsl.trigger.config
        if hasattr(config, "cron"):
            cron_expr = config.cron
            timezone_str = getattr(config, "timezone", "UTC")

    # 1. Create the Workflow row
    workflow_db = Workflow(
        id=uuid.UUID(dsl.id) if _is_valid_uuid(dsl.id) else uuid.uuid4(),
        user_id=user_id,
        name=workflow_name,
        description=dsl.description,
        status=WorkflowStatus.draft,
        original_prompt=original_prompt,
        ai_context_json=dsl.to_db_dict(),
        cron_expression=cron_expr,
        timezone=timezone_str,
        version=dsl.version,
    )
    db.add(workflow_db)
    db.flush()  # Get the workflow ID without committing yet

    # 2. Create WorkflowNode rows
    node_id_map: dict[str, uuid.UUID] = {}  # dsl_node_id → db_uuid
    for node in dsl.nodes:
        db_node_id = uuid.uuid4()
        node_id_map[node.id] = db_node_id

        db_node = WorkflowNode(
            id=db_node_id,
            workflow_id=workflow_db.id,
            node_type=node.type.value,
            label=node.label,
            config_json={
                "dsl_id": node.id,
                "service": node.service.value,
                "operation": node.operation.value,
                "params": node.params,
                "on_success": node.on_success,
                "on_failure": node.on_failure,
                "retry_policy": node.retry_policy.model_dump() if node.retry_policy else None,
                "timeout_seconds": node.timeout_seconds,
            },
            position_x=0.0,  # Visual positions set by frontend later
            position_y=0.0,
            is_disabled=node.is_disabled,
        )
        db.add(db_node)

    db.flush()  # Ensure node IDs exist before creating edges

    # 3. Create WorkflowEdge rows
    for edge in dsl.edges:
        source_db_id = node_id_map.get(edge.source_id)
        target_db_id = node_id_map.get(edge.target_id)

        if source_db_id and target_db_id:
            db_edge = WorkflowEdge(
                id=uuid.uuid4(),
                workflow_id=workflow_db.id,
                source_node_id=source_db_id,
                target_node_id=target_db_id,
                label=edge.label,
                condition_expr=edge.condition,
            )
            db.add(db_edge)

    db.commit()
    db.refresh(workflow_db)
    logger.info(f"Saved workflow '{workflow_name}' with ID {workflow_db.id} for user {user_id}")
    return workflow_db


def _is_valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


# ─────────────────────────────────────────────────────────────────────────────
# GROQ LLM CALL
# ─────────────────────────────────────────────────────────────────────────────

def _call_groq(
    groq_client: Groq,
    messages: list[dict],
) -> str:
    """Make a single Groq API call and return the raw text content."""
    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        max_tokens=GROQ_MAX_TOKENS,
        temperature=GROQ_TEMPERATURE,
        response_format={"type": "json_object"},  # Force JSON output mode
    )
    return response.choices[0].message.content


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PLANNER FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

async def plan_workflow(
    workflow_name: str,
    intent: IntentDetails,
    user_id: uuid.UUID,
    db: Session,
    existing_dsl: Optional[dict] = None,
) -> PlanWorkflowResponse:
    """
    Main planner entry point.

    When `existing_dsl` is supplied the model is instructed to *incrementally
    modify* the existing workflow rather than generate a fresh one.  Stable
    node IDs are preserved so the React-Flow canvas doesn't jump around.

    Steps:
      1. Build the user message from the intent
      2. Call Groq with the system prompt
      3. Extract + parse DSL JSON (with retries on failure)
      4. Run graph validation
      5. Save to DB
      6. Return full response
    """
    groq_client = Groq(api_key=settings.GROQ_API_KEY)

    # Extract operations from the intent so we can filter the schema block to
    # only the ops this workflow will actually use — shorter prompt, same effect.
    relevant_operations: list[str] | None = None
    if intent.integrations:
        # Map integration names to their common operations for prompt filtering
        _service_ops = {
            "gmail":          ["send_email", "get_emails", "create_draft"],
            "google_sheets":  ["read_rows", "append_row", "update_row", "find_row"],
            "google_calendar": ["create_event", "list_events"],
            "slack":          ["post_message"],
            "notion":         ["append_row"],
            "hubspot":        ["append_row", "update_row", "find_row"],
            "http":           ["http_request"],
            "groq":           ["llm_generate", "llm_classify", "llm_extract"],
            "openai":         ["llm_generate", "llm_classify", "llm_extract"],
        }
        relevant_operations = []
        for svc in intent.integrations:
            relevant_operations.extend(_service_ops.get(svc.lower(), []))
        # Always include builtin ops (conditions, waits, etc.)
        relevant_operations.extend(
            ["condition_branch", "for_each", "wait", "map_fields", "filter_list", "set_variable"]
        )
        relevant_operations = list(dict.fromkeys(relevant_operations))  # deduplicate, preserve order

    system_prompt = build_system_prompt(existing_dsl=existing_dsl, operations=relevant_operations)

    # Build the user message from the structured intent
    user_message = _build_user_message(workflow_name, intent, existing_dsl=existing_dsl)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_message},
    ]

    attempt = 0
    last_raw: str = ""
    last_errors: list[str] = []

    while attempt <= MAX_RETRIES:
        attempt += 1

        # ── LLM Call ────────────────────────────────────────────────────────
        if attempt > 1:
            # Retry: inject the error feedback into the conversation
            logger.warning(f"Retrying Groq call (attempt {attempt}) for workflow '{workflow_name}'")
            messages.append({"role": "assistant", "content": last_raw})
            messages.append({
                "role": "user",
                "content": build_retry_prompt(last_raw, last_errors),
            })

        try:
            raw_response = _call_groq(groq_client, messages)
        except Exception as e:
            logger.error(f"Groq API call failed on attempt {attempt}: {e}")
            if attempt > MAX_RETRIES:
                raise RuntimeError(f"Groq API failed after {attempt} attempts: {e}") from e
            continue

        last_raw = raw_response
        last_errors = []

        # ── JSON Extraction ──────────────────────────────────────────────────
        json_str = _extract_json(raw_response)

        # ── Pydantic Validation ──────────────────────────────────────────────
        try:
            raw_dict = json.loads(json_str)
        except json.JSONDecodeError as e:
            last_errors = [f"Invalid JSON returned by LLM: {e}"]
            logger.warning(f"Attempt {attempt}: JSON parse error — {e}")
            continue

        # Inject the workflow name if the LLM didn't set it
        if not raw_dict.get("name"):
            raw_dict["name"] = workflow_name

        try:
            dsl = WorkflowDSL.model_validate(raw_dict)
        except ValidationError as e:
            last_errors = [f"Schema error: {err['msg']} at {'.'.join(str(x) for x in err['loc'])}"
                           for err in e.errors()]
            logger.warning(f"Attempt {attempt}: Pydantic validation failed — {last_errors}")
            continue

        # ── Graph Validation ─────────────────────────────────────────────────
        graph_result: ValidationResult = validate_workflow_graph(dsl)

        # ── Schema Param Validation ─────────────────────────────────────────
        schema_result = check_schema(dsl)

        # Consolidate ALL hard errors from both checks into one list[str].
        # graph_result.errors  → List[str]      (old dsl/validator.py)
        # schema_result.errors → List[ValidationIssue]  (new validator/models.py)
        # Both are serialised to strings so build_retry_prompt receives a uniform list.
        combined_error_strings: list[str] = list(graph_result.errors) + [
            f"{e.code} on node '{e.node_id}': {e.message}" if e.node_id else f"{e.code}: {e.message}"
            for e in schema_result.errors
        ]

        if combined_error_strings:
            last_errors = combined_error_strings
            logger.warning(
                f"Attempt {attempt}: Validation failed — "
                f"{len(graph_result.errors)} graph error(s), "
                f"{len(schema_result.errors)} schema error(s)"
            )
            continue



        # ── SUCCESS — Save to DB ─────────────────────────────────────────────
        logger.info(f"DSL validated successfully on attempt {attempt} for '{workflow_name}'")

        workflow_db = _save_workflow_to_db(
            dsl=dsl,
            workflow_name=workflow_name,
            original_prompt=user_message,
            user_id=user_id,
            db=db,
        )

        return PlanWorkflowResponse(
            workflow_id=workflow_db.id,
            workflow_name=workflow_db.name,
            dsl=dsl.to_db_dict(),
            graph_stats=_compute_graph_stats(dsl),
            validation_warnings=graph_result.warnings,
            groq_attempts=attempt,
            created_at=workflow_db.created_at,
        )

    # ── All retries exhausted ────────────────────────────────────────────────
    error_summary = "; ".join(last_errors)
    logger.error(
        f"Workflow planning failed after {MAX_RETRIES + 1} attempts for '{workflow_name}'. "
        f"Last errors: {error_summary}"
    )
    raise ValueError(
        f"Could not generate a valid workflow after {MAX_RETRIES + 1} attempts. "
        f"Validation errors: {error_summary}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# INTENT → USER MESSAGE
# ─────────────────────────────────────────────────────────────────────────────

def _build_user_message(workflow_name: str, intent: IntentDetails, existing_dsl: Optional[dict] = None) -> str:
    """
    Convert the structured IntentDetails into a clear user message for Groq.
    Presenting it as structured JSON gives the model clear, unambiguous input.

    When existing_dsl is provided, the message instructs the model to modify
    only the parts of the existing workflow that are relevant to the new intent,
    and to PRESERVE all other node IDs and structure unchanged.
    """
    intent_dict = {
        "workflow_name": workflow_name,
        "goal": intent.goal,
        "trigger": intent.trigger,
        "industry": intent.industry,
        "integrations_needed": intent.integrations,
        "additional_details": intent.extra_details or {},
    }

    if existing_dsl:
        return (
            "INCREMENTAL EDIT REQUEST:\n"
            "The user wants to modify their existing workflow. "
            "Apply ONLY the changes described in the edit request below. "
            "Preserve all existing node IDs exactly as-is — do NOT rename or reorder any node that is not being changed. "
            "Only add, remove, or adjust the nodes/edges that are relevant to the edit.\n\n"
            f"EXISTING WORKFLOW DSL:\n{json.dumps(existing_dsl, indent=2)}\n\n"
            f"EDIT REQUEST:\n{json.dumps(intent_dict, indent=2)}"
        )

    return (
        "Generate a complete AutoFlow DSL JSON for the following automation workflow:\n\n"
        + json.dumps(intent_dict, indent=2)
    )
