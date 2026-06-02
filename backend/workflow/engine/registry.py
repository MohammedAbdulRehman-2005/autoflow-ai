"""
AutoFlow AI X — Executor Registry
=====================================
Maps "service.operation" keys to executor instances.

To add a new integration:
  1. Create a new executor class in executors/yourservice.py
  2. Import it here
  3. Register it with @register or add to EXECUTOR_REGISTRY directly
  4. Done — the runner will automatically dispatch to it

The registry uses a singleton pattern (one instance per executor class)
to avoid re-initialization overhead per node execution.
"""

import logging
from typing import Optional

from backend.workflow.engine.executors.base import BaseExecutor

# ── Import all executor implementations ──────────────────────────────────────
from backend.workflow.engine.executors.builtin import (
    ConditionBranchExecutor,
    FilterListExecutor,
    ForEachExecutor,
    MapFieldsExecutor,
    SetVariableExecutor,
    TriggerExecutor,
    WaitExecutor,
)
from backend.workflow.engine.executors.gmail import (
    GmailGetEmailsExecutor,
    GmailSendEmailExecutor,
)
from backend.workflow.engine.executors.google_sheets import (
    SheetsAppendRowExecutor,
    SheetsFindRowExecutor,
    SheetsReadRowsExecutor,
    SheetsUpdateRowExecutor,
)
from backend.workflow.engine.executors.http import HttpRequestExecutor
from backend.workflow.engine.executors.ai_agent import (
    LLMClassifyExecutor,
    LLMExtractExecutor,
    LLMGenerateExecutor,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# EXECUTOR REGISTRY
# Format: "service.operation" → executor instance
# ─────────────────────────────────────────────────────────────────────────────

EXECUTOR_REGISTRY: dict[str, BaseExecutor] = {
    # ── Built-in (no external API) ────────────────────────────────────────────
    "scheduler.cron":              TriggerExecutor(),
    "scheduler.manual_trigger":    TriggerExecutor(),
    "scheduler.webhook_listen":    TriggerExecutor(),
    "builtin.condition_branch":    ConditionBranchExecutor(),
    "builtin.for_each":            ForEachExecutor(),
    "builtin.wait":                WaitExecutor(),
    "builtin.map_fields":          MapFieldsExecutor(),
    "builtin.filter_list":         FilterListExecutor(),
    "builtin.set_variable":        SetVariableExecutor(),

    # ── Gmail ─────────────────────────────────────────────────────────────────
    "gmail.send_email":            GmailSendEmailExecutor(),
    "gmail.get_emails":            GmailGetEmailsExecutor(),
    "gmail.create_draft":          GmailSendEmailExecutor(),   # Same interface as send

    # ── Google Sheets ─────────────────────────────────────────────────────────
    "google_sheets.read_rows":     SheetsReadRowsExecutor(),
    "google_sheets.append_row":    SheetsAppendRowExecutor(),
    "google_sheets.update_row":    SheetsUpdateRowExecutor(),
    "google_sheets.find_row":      SheetsFindRowExecutor(),

    # ── HTTP / Webhooks ───────────────────────────────────────────────────────
    "http.http_request":           HttpRequestExecutor(),

    # ── AI Agents ─────────────────────────────────────────────────────────────
    "groq.llm_generate":           LLMGenerateExecutor(),
    "groq.llm_classify":           LLMClassifyExecutor(),
    "groq.llm_extract":            LLMExtractExecutor(),
    "openai.llm_generate":         LLMGenerateExecutor(),    # Same interface for now
    "openai.llm_classify":         LLMClassifyExecutor(),
    "openai.llm_extract":          LLMExtractExecutor(),
}


def get_executor(service: str, operation: str) -> Optional[BaseExecutor]:
    """
    Look up an executor by service + operation.

    Returns None if no executor is registered for the combination.
    The runner should fail the node gracefully when None is returned.
    """
    key = f"{service}.{operation}"
    executor = EXECUTOR_REGISTRY.get(key)
    if executor is None:
        logger.warning(
            f"No executor registered for '{key}'. "
            f"Available: {sorted(EXECUTOR_REGISTRY.keys())}"
        )
    return executor


def register(service: str, operation: str, executor: BaseExecutor) -> None:
    """
    Dynamically register a new executor at runtime.
    Useful for plugins and integration tests.
    """
    key = f"{service}.{operation}"
    EXECUTOR_REGISTRY[key] = executor
    logger.info(f"Registered executor for '{key}': {executor.__class__.__name__}")


def list_supported_operations() -> list[str]:
    """Return all registered service.operation keys (for documentation/API)."""
    return sorted(EXECUTOR_REGISTRY.keys())
