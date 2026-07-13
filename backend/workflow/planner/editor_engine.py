"""
AutoFlow AI X — Editor Engine  (RFC-001 §2, §4)  [formerly editor_service.py]
==============================================================================
Handles the POST /ai/add-step endpoint.

Design rules (Sprint 3 approved plan):
  - Registry-first: always try CapabilityRegistry.match() before falling back to the LLM.
  - Returns ONLY a delta (new_nodes, new_edges, removed_edges) — never a full graph.
  - New nodes are built from NodeRegistry.default_params — LLM only identifies
    WHICH plugin to use (service + operation), not the params themselves.
  - Node IDs are generated here using a collision-safe short-UUID suffix.
  - Edge splicing: if insert_after_node_id is set and that node has an outgoing
    edge, the old edge is removed and two new edges are added.

Sprint 3.5: Renamed from editor_service.py. Observability instrumentation added.
"""

from __future__ import annotations

import json
import logging
import re
import uuid as uuid_module
from typing import Any, Dict, List, Optional

from groq import Groq

from backend.core.config import get_settings
from backend.workflow.capability_registry import CapabilityRegistry
from backend.workflow.node_registry import NodeRegistry
from backend.workflow.observability import SpanCollection, SPAN_PLANNER, SPAN_CAPABILITY_MATCH
from backend.workflow.planner.schemas import (
    AddStepResponse,
    CapabilityMatchDTO,
    DeltaResult,
    EdgePairDTO,
)

logger = logging.getLogger(__name__)
settings = get_settings()

GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_MAX_TOKENS = 512          # We only need a small JSON fragment
GROQ_TEMPERATURE = 0.1         # Very low — deterministic node selection
CAPABILITY_CONFIDENCE_THRESHOLD = 0.40  # Minimum to prefer registry over LLM


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

async def add_step(
    current_dsl: Dict[str, Any],
    user_intent: str,
    insert_after_node_id: Optional[str],
    workflow_id: Optional[uuid_module.UUID] = None,
) -> AddStepResponse:
    """
    Add one or more nodes to an existing workflow DSL.

    Algorithm
    ---------
    1. Try CapabilityRegistry.match(user_intent).
       If confidence >= CAPABILITY_CONFIDENCE_THRESHOLD → expand pattern (registry-driven).
    2. Otherwise → call Groq to identify a single service+operation, then look
       up that plugin in NodeRegistry (still registry-driven; LLM doesn't write params).
    3. Generate safe node IDs.
    4. Compute edge delta (new edges + removed edges for splice insertions).
    5. Return AddStepResponse with delta only — never full graph.
    """
    existing_node_ids = {n["id"] for n in current_dsl.get("nodes", [])}

    # ── Step 1: Capability Registry match ────────────────────────────────────
    cap_match = CapabilityRegistry.match(user_intent)
    if cap_match and cap_match.confidence >= CAPABILITY_CONFIDENCE_THRESHOLD:
        logger.info(
            "Capability match: %s (confidence=%.2f, keywords=%s)",
            cap_match.pattern.name,
            cap_match.confidence,
            cap_match.matched_keywords,
        )
        return _build_response_from_capability(
            cap_match=cap_match,
            current_dsl=current_dsl,
            existing_node_ids=existing_node_ids,
            insert_after_node_id=insert_after_node_id,
        )

    # ── Step 2: LLM selects plugin, NodeRegistry provides params ─────────────
    logger.info("No capability match (or low confidence). Calling LLM for plugin selection.")
    plugin_key = await _llm_select_plugin(user_intent, current_dsl)

    if plugin_key:
        parts = plugin_key.split(".", 1)
        service, operation = (parts[0], parts[1]) if len(parts) == 2 else (None, None)
        plugin = NodeRegistry.get(service, operation) if service and operation else None
    else:
        plugin = None

    if not plugin:
        # Graceful fallback — default to groq.llm_generate
        logger.warning("LLM did not return a valid plugin key. Defaulting to groq.llm_generate.")
        plugin = NodeRegistry.get("groq", "llm_generate")

    if not plugin:
        raise RuntimeError("No suitable plugin found and default plugin unavailable.")

    new_node_id = _safe_id(f"{plugin.service}_{plugin.operation}", existing_node_ids)
    new_node = _build_node_from_plugin(plugin, new_node_id)
    existing_node_ids.add(new_node_id)

    # Determine edge delta
    new_edges, removed_edges = _compute_edge_delta(
        current_dsl=current_dsl,
        new_node_ids=[new_node_id],
        first_new_node_id=new_node_id,
        last_new_node_id=new_node_id,
        insert_after_node_id=insert_after_node_id,
    )

    explanation = (
        f"Added **{plugin.label}** ({plugin.service}.{plugin.operation}) based on your request. "
        f"This node uses the registered default parameters — open the Node Inspector to customise them. "
        f"Nodes are wired using registry-provided defaults, not LLM-generated params."
    )

    return AddStepResponse(
        delta=DeltaResult(
            new_nodes=[new_node],
            new_edges=[{"source_id": e[0], "target_id": e[1]} for e in new_edges],
            removed_edges=[EdgePairDTO(source_id=r[0], target_id=r[1]) for r in removed_edges],
        ),
        explanation=explanation,
        capability_match=None,
        applied_node_ids=[new_node_id],
        registry_driven=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _build_response_from_capability(
    cap_match,
    current_dsl: Dict[str, Any],
    existing_node_ids: set,
    insert_after_node_id: Optional[str],
) -> AddStepResponse:
    """Expand a capability pattern into a delta using NodeRegistry defaults."""
    pattern = cap_match.pattern
    new_node_ids: List[str] = []
    new_nodes: List[Dict[str, Any]] = []

    for node_key in pattern.nodes:
        parts = node_key.split(".", 1)
        if len(parts) != 2:
            continue
        service, operation = parts
        plugin = NodeRegistry.get(service, operation)
        if not plugin:
            logger.warning("Capability %s references unknown plugin %s — skipping.", pattern.name, node_key)
            continue

        nid = _safe_id(f"{service}_{operation}", existing_node_ids)
        existing_node_ids.add(nid)
        new_node_ids.append(nid)
        new_nodes.append(_build_node_from_plugin(plugin, nid))

    if not new_node_ids:
        raise RuntimeError(f"Capability '{pattern.name}' expanded to zero valid nodes.")

    # Build intra-capability edges using the pattern's edge topology
    intra_edges: List[tuple] = []
    for (from_idx, to_idx) in pattern.edges:
        if from_idx < len(new_node_ids) and to_idx < len(new_node_ids):
            intra_edges.append((new_node_ids[from_idx], new_node_ids[to_idx]))

    # If no edges defined (shouldn't happen), fall back to linear chain
    if not intra_edges:
        intra_edges = [(new_node_ids[i], new_node_ids[i+1]) for i in range(len(new_node_ids) - 1)]

    # Connection edges to the rest of the workflow
    connection_edges, removed_edges = _compute_edge_delta(
        current_dsl=current_dsl,
        new_node_ids=new_node_ids,
        first_new_node_id=new_node_ids[0],
        last_new_node_id=new_node_ids[-1],
        insert_after_node_id=insert_after_node_id,
    )

    all_new_edges = intra_edges + connection_edges

    cap_dto = CapabilityMatchDTO(
        capability_name=pattern.name,
        description=pattern.description,
        confidence=cap_match.confidence,
        matched_keywords=cap_match.matched_keywords,
        explanation=pattern.explanation,
        tags=pattern.tags,
        node_count=len(new_node_ids),
    )

    return AddStepResponse(
        delta=DeltaResult(
            new_nodes=new_nodes,
            new_edges=[{"source_id": s, "target_id": t} for s, t in all_new_edges],
            removed_edges=[EdgePairDTO(source_id=r[0], target_id=r[1]) for r in removed_edges],
        ),
        explanation=pattern.explanation,
        capability_match=cap_dto,
        applied_node_ids=new_node_ids,
        registry_driven=True,
    )


def _build_node_from_plugin(plugin, node_id: str) -> Dict[str, Any]:
    """Build a WorkflowNodeDSL dict from NodeRegistry defaults — no LLM involved."""
    return {
        "id": node_id,
        "type": plugin.node_type,
        "service": plugin.service,
        "operation": plugin.operation,
        "label": plugin.label,
        "params": dict(plugin.default_params),
        "credential_id": None,
        "on_success": None,
        "on_failure": None,
        "error_policy": "stop",
        "notes": None,
        "display_note_in_flow": False,
        "always_output_data": False,
        "execute_once": False,
    }


def _safe_id(base: str, existing_ids: set, max_attempts: int = 20) -> str:
    """
    Generate a unique node ID of form '{base}_{4-char-hex}'.
    Guarantees no collision with existing_ids.
    ID matches DSL pattern: ^[a-z][a-z0-9_]*$
    """
    # Sanitise base: lowercase, replace non-alnum with _, strip leading underscores
    base = re.sub(r"[^a-z0-9]", "_", base.lower()).strip("_")
    if not base or not base[0].isalpha():
        base = "node_" + base

    for _ in range(max_attempts):
        suffix = uuid_module.uuid4().hex[:4]
        candidate = f"{base}_{suffix}"
        if candidate not in existing_ids:
            return candidate

    # Extremely unlikely — just use full UUID
    return f"{base}_{uuid_module.uuid4().hex[:8]}"


def _compute_edge_delta(
    current_dsl: Dict[str, Any],
    new_node_ids: List[str],
    first_new_node_id: str,
    last_new_node_id: str,
    insert_after_node_id: Optional[str],
) -> tuple:
    """
    Compute (new_connection_edges, removed_edges) for wiring the new node(s)
    into the existing graph.

    Returns
    -------
    new_connection_edges : List[(source_id, target_id)]
    removed_edges        : List[(source_id, target_id)]
    """
    existing_edges: List[Dict[str, Any]] = current_dsl.get("edges", [])
    existing_nodes: List[Dict[str, Any]] = current_dsl.get("nodes", [])

    new_connection_edges: List[tuple] = []
    removed_edges: List[tuple] = []

    if insert_after_node_id:
        # Find outgoing edges from insert_after_node_id
        outgoing = [
            e for e in existing_edges
            if e["source_id"] == insert_after_node_id
        ]
        # Splice: remove each outgoing edge and replace with:
        #   insert_after → first_new, last_new → old_target
        for e in outgoing:
            removed_edges.append((e["source_id"], e["target_id"]))
            new_connection_edges.append((last_new_node_id, e["target_id"]))

        # Connect insert_after → first new node
        new_connection_edges.append((insert_after_node_id, first_new_node_id))

    else:
        # Append mode: connect from the last existing non-new node
        existing_node_ids = {n["id"] for n in existing_nodes}
        new_ids_set = set(new_node_ids)

        # Find the "last" node: the one with no outgoing edges (or the last in list)
        nodes_with_outgoing = {e["source_id"] for e in existing_edges}
        terminal_nodes = [
            n["id"] for n in existing_nodes
            if n["id"] not in nodes_with_outgoing and n["id"] not in new_ids_set
        ]

        if terminal_nodes:
            anchor = terminal_nodes[-1]
        elif existing_nodes:
            anchor = existing_nodes[-1]["id"]
        else:
            anchor = None

        if anchor and anchor not in new_ids_set:
            new_connection_edges.append((anchor, first_new_node_id))

    return new_connection_edges, removed_edges


async def _llm_select_plugin(user_intent: str, current_dsl: Dict[str, Any]) -> Optional[str]:
    """
    Ask the LLM to pick the BEST plugin key from the registered plugins.
    Returns a "service.operation" string or None on failure.

    This function is intentionally narrow: the LLM only selects a plugin key.
    All parameter generation comes from NodeRegistry.default_params.
    """
    plugins = NodeRegistry.list_all()
    plugin_list = "\n".join(
        f"  {p.service}.{p.operation}: {p.label}"
        for p in plugins
        if p.node_type != "trigger"  # Don't suggest adding triggers mid-flow
    )

    existing_nodes = current_dsl.get("nodes", [])
    node_context = ", ".join(
        f"{n.get('label', n.get('id', '?'))} ({n.get('type', '?')})"
        for n in existing_nodes[-3:]  # Last 3 for brevity
    ) or "empty workflow"

    system = (
        "You are an AutoFlow workflow node selector. "
        "Your ONLY job is to pick the single best plugin key from the list below. "
        "Respond with ONLY valid JSON: {\"plugin\": \"service.operation\", \"reason\": \"...\"}. "
        "Do not add any other text."
    )

    user_msg = (
        f"User wants to add a step: \"{user_intent}\"\n"
        f"Current workflow ends with: {node_context}\n\n"
        f"Available plugins:\n{plugin_list}\n\n"
        "Pick the SINGLE best plugin. Return JSON only."
    )

    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=GROQ_MAX_TOKENS,
            temperature=GROQ_TEMPERATURE,
        )
        raw = response.choices[0].message.content.strip()
        # Extract JSON even if the model wrapped it in markdown
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return data.get("plugin")
    except Exception as exc:
        logger.warning("LLM plugin selection failed: %s", exc)

    return None
