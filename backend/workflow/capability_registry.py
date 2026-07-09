"""
AutoFlow AI X — Capability Registry  (RFC-001 §4)
===================================================
A static registry of multi-node "capability patterns" that map a human-readable
capability name to an ordered sequence of NodePlugin keys + suggested edge topology.

Design rules (Sprint 3 approved plan):
  - This is the backend source of truth — never duplicated on the frontend.
  - Exposed through the /ai/capabilities API endpoint.
  - CapabilityRegistry.match() returns confidence (0.0–1.0) + matched_keywords
    for future explainability; the caller decides whether to use the match.
  - Registry-driven expansion is preferred over LLM-generated node JSON.
  - Patterns encode their edges as index pairs so the editor_service can build
    a fully-wired DSL delta without LLM assistance.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# DATA MODELS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CapabilityPattern:
    """
    A named multi-node pattern that can be expanded into concrete DSL nodes.

    Attributes
    ----------
    name        : Human-readable name, e.g. "Invoice Processing"
    description : One-sentence description shown in the UI
    keywords    : Trigger words / phrases (case-insensitive, substring match)
    nodes       : Ordered list of "service.operation" plugin keys to expand
    edges       : (from_idx, to_idx) pairs into `nodes` — defines the topology.
                  Use sequential [(0,1),(1,2),...] for a linear chain.
    explanation : "Why this change?" text surfaced in the DiffPreview UI.
    tags        : Optional tags for future filtering (e.g. "ai", "email", "data")
    """
    name: str
    description: str
    keywords: List[str]
    nodes: List[str]                           # "service.operation"
    edges: List[Tuple[int, int]]               # index pairs into nodes
    explanation: str
    tags: List[str] = field(default_factory=list)


@dataclass
class CapabilityMatch:
    """
    Result of CapabilityRegistry.match().

    confidence       : 0.0–1.0 — fraction of query tokens that matched keywords.
    matched_keywords : The exact keywords from the pattern that were found in the query.
    pattern          : The matched CapabilityPattern (or None if no match).
    """
    pattern: CapabilityPattern
    confidence: float
    matched_keywords: List[str]


# ─────────────────────────────────────────────────────────────────────────────
# REGISTRY
# ─────────────────────────────────────────────────────────────────────────────

class CapabilityRegistry:
    """
    Static registry of multi-node workflow capability patterns.

    Usage
    -----
    from backend.workflow.capability_registry import CapabilityRegistry

    match = CapabilityRegistry.match("process invoices and notify finance team")
    if match and match.confidence >= 0.4:
        nodes = match.pattern.nodes   # ["groq.llm_extract", ...]
    """
    _patterns: List[CapabilityPattern] = []

    @classmethod
    def register(cls, pattern: CapabilityPattern) -> None:
        """Add a pattern to the registry."""
        cls._patterns.append(pattern)

    @classmethod
    def list_all(cls) -> List[CapabilityPattern]:
        """Return all registered patterns (for the /ai/capabilities API)."""
        return list(cls._patterns)

    @classmethod
    def match(cls, query: str) -> Optional[CapabilityMatch]:
        """
        Keyword-score the query against all registered patterns.

        Scoring algorithm:
          For each pattern, tokenise the query and count how many of the pattern's
          keywords appear as whole-word (or substring) matches in the query.
          confidence = matched_count / len(pattern.keywords)

        Returns the best match with confidence >= 0.15, or None.
        The threshold is intentionally low so partial matches surface — the
        editor_service decides the final confidence threshold.
        """
        if not query or not cls._patterns:
            return None

        query_lower = query.lower()
        # Tokenise into words + bigrams for multi-word keyword matching
        words = re.findall(r"[a-z0-9]+", query_lower)
        bigrams = [" ".join(words[i:i+2]) for i in range(len(words) - 1)]
        query_tokens = set(words) | set(bigrams)

        best: Optional[CapabilityMatch] = None

        for pattern in cls._patterns:
            matched = []
            for kw in pattern.keywords:
                kw_lower = kw.lower().strip()
                # Accept substring match OR whole-word match
                if kw_lower in query_lower or kw_lower in query_tokens:
                    matched.append(kw)

            if not matched:
                continue

            confidence = len(matched) / len(pattern.keywords)

            if best is None or confidence > best.confidence:
                best = CapabilityMatch(
                    pattern=pattern,
                    confidence=round(confidence, 3),
                    matched_keywords=matched,
                )

        if best and best.confidence >= 0.15:
            return best

        return None


# ─────────────────────────────────────────────────────────────────────────────
# BUILT-IN PATTERNS  (RFC-001 §4 examples + AutoFlow-native additions)
# ─────────────────────────────────────────────────────────────────────────────

CapabilityRegistry.register(CapabilityPattern(
    name="Invoice Processing",
    description="Extract data from an invoice → validate with AI → notify team",
    keywords=["invoice", "ocr", "receipt", "bill", "scan", "extract invoice", "process invoice"],
    nodes=[
        "groq.llm_extract",
        "builtin.condition_branch",
        "gmail.send_email",
    ],
    edges=[(0, 1), (1, 2)],
    explanation=(
        "Invoice Processing is a 3-step pattern: an AI extraction node reads "
        "the document, a condition branch validates the result, and a Gmail node "
        "notifies the finance team on success or failure."
    ),
    tags=["ai", "finance", "email"],
))

CapabilityRegistry.register(CapabilityPattern(
    name="Meeting Assistant",
    description="Scheduled trigger → AI meeting summary → Slack notification",
    keywords=["meeting", "calendar", "summary", "notes", "recap", "meeting summary", "meeting notes"],
    nodes=[
        "scheduler.cron",
        "groq.llm_generate",
        "slack.post_message",
    ],
    edges=[(0, 1), (1, 2)],
    explanation=(
        "Meeting Assistant runs on a schedule, uses Groq AI to generate a "
        "meeting summary or recap, then posts it to a Slack channel automatically."
    ),
    tags=["ai", "scheduling", "slack"],
))

CapabilityRegistry.register(CapabilityPattern(
    name="Lead Qualification",
    description="AI scores an incoming lead → branch on score → notify sales",
    keywords=["lead", "crm", "score", "qualify", "qualification", "hubspot", "prospect", "sales lead"],
    nodes=[
        "groq.llm_classify",
        "builtin.condition_branch",
        "gmail.send_email",
    ],
    edges=[(0, 1), (1, 2)],
    explanation=(
        "Lead Qualification uses Groq AI to classify and score a prospect, "
        "then routes to a condition branch: high-score leads get an immediate "
        "follow-up email; low-score leads are filtered out."
    ),
    tags=["ai", "crm", "email"],
))

CapabilityRegistry.register(CapabilityPattern(
    name="Email Triage",
    description="Read inbox → AI classify → route to Slack",
    keywords=["triage", "inbox", "categorise", "categorize", "filter email", "email triage", "classify email"],
    nodes=[
        "gmail.get_emails",
        "groq.llm_classify",
        "slack.post_message",
    ],
    edges=[(0, 1), (1, 2)],
    explanation=(
        "Email Triage reads your Gmail inbox, uses Groq AI to classify each "
        "message (support request, sales inquiry, spam, etc.), then posts a "
        "routed summary to the appropriate Slack channel."
    ),
    tags=["ai", "email", "slack"],
))

CapabilityRegistry.register(CapabilityPattern(
    name="Data Validation Pipeline",
    description="Extract structured data → validate → store or notify on failure",
    keywords=["validate", "validation", "extract data", "check data", "data quality", "verify"],
    nodes=[
        "groq.llm_extract",
        "builtin.condition_branch",
        "slack.post_message",
    ],
    edges=[(0, 1), (1, 2)],
    explanation=(
        "Data Validation extracts structured data with Groq AI, then runs a "
        "condition check against your business rules. Valid records proceed; "
        "invalid records trigger a Slack alert for manual review."
    ),
    tags=["ai", "data", "validation"],
))

CapabilityRegistry.register(CapabilityPattern(
    name="AI Summary + Notify",
    description="Generate an AI summary of any text and send it via email or Slack",
    keywords=["summarize", "summarise", "summary", "digest", "brief", "recap", "tldr", "tl;dr"],
    nodes=[
        "groq.llm_generate",
        "slack.post_message",
    ],
    edges=[(0, 1)],
    explanation=(
        "AI Summary + Notify generates a plain-language summary of your input "
        "using Groq AI, then immediately posts it to a Slack channel. "
        "Ideal for daily digests, report summaries, or meeting recaps."
    ),
    tags=["ai", "slack"],
))
