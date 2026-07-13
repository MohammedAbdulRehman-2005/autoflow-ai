"""
AutoFlow AI X — Validation Error Codes & Models
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# ERROR CODES  (machine-readable, used by frontend for highlighting)
# ─────────────────────────────────────────────────────────────────────────────

class ErrorCode(str, Enum):
    # ── Schema ────────────────────────────────────────────────────────────────
    MISSING_REQUIRED_PARAM   = "MISSING_REQUIRED_PARAM"
    INVALID_PARAM_TYPE       = "INVALID_PARAM_TYPE"
    INVALID_CRON_EXPRESSION  = "INVALID_CRON_EXPRESSION"
    MISSING_TRIGGER_NODE     = "MISSING_TRIGGER_NODE"
    MULTIPLE_TRIGGER_NODES   = "MULTIPLE_TRIGGER_NODES"

    # ── Credentials / Integrations ────────────────────────────────────────────
    MISSING_CREDENTIAL       = "MISSING_CREDENTIAL"
    INVALID_CREDENTIAL       = "INVALID_CREDENTIAL"

    # ── Graph Structure ───────────────────────────────────────────────────────
    UNREACHABLE_NODE         = "UNREACHABLE_NODE"
    CYCLE_DETECTED           = "CYCLE_DETECTED"
    DEAD_END_ACTION_NODE     = "DEAD_END_ACTION_NODE"       # warning
    MISSING_CONDITION_BRANCH = "MISSING_CONDITION_BRANCH"   # warning
    MISSING_FAILURE_HANDLER  = "MISSING_FAILURE_HANDLER"    # warning

    # ── Template Variables ────────────────────────────────────────────────────
    UNDEFINED_TEMPLATE_VAR   = "UNDEFINED_TEMPLATE_VAR"
    FORWARD_REFERENCE        = "FORWARD_REFERENCE"          # warning: referencing a node that may not have run
    MISSING_WORKFLOW_VAR     = "MISSING_WORKFLOW_VAR"

    # ── Schedule ─────────────────────────────────────────────────────────────
    SCHEDULE_CONFLICT        = "SCHEDULE_CONFLICT"
    INVALID_SCHEDULE         = "INVALID_SCHEDULE"

    # ── Sprint 1 bug fixes ───────────────────────────────────────────────────
    # Bug #1: condition expression references an output key that doesn't exist
    CONDITION_KEY_MISMATCH   = "CONDITION_KEY_MISMATCH"
    # Bug #2: Slack channel looks like a placeholder value (e.g. 'all-xyz')
    PLACEHOLDER_CHANNEL      = "PLACEHOLDER_CHANNEL"
    # Bug #3: node.on_success/on_failure disagrees with the DSL edges array
    ROUTING_DRIFT            = "ROUTING_DRIFT"


# ─────────────────────────────────────────────────────────────────────────────
# VALIDATION ERROR / WARNING
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ValidationIssue:
    """
    A single validation finding.
    severity="error"   → blocks saving/execution
    severity="warning" → advisory, does not block
    """
    code: str                         # ErrorCode value
    message: str                      # Human-readable description
    node_id: Optional[str] = None     # Which DSL node caused this (None = workflow-level)
    severity: str = "error"           # "error" | "warning"
    detail: Optional[Dict[str, Any]] = None  # Extra context for frontend

    def to_dict(self) -> dict:
        out = {
            "code":     self.code,
            "message":  self.message,
            "severity": self.severity,
        }
        if self.node_id is not None:
            out["node_id"] = self.node_id
        if self.detail:
            out["detail"] = self.detail
        return out


# ─────────────────────────────────────────────────────────────────────────────
# VALIDATION RESULT
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ValidationResult:
    issues: List[ValidationIssue] = field(default_factory=list)

    def add_error(
        self,
        code: str,
        message: str,
        node_id: Optional[str] = None,
        detail: Optional[dict] = None,
    ) -> None:
        self.issues.append(
            ValidationIssue(code=code, message=message, node_id=node_id,
                            severity="error", detail=detail)
        )

    def add_warning(
        self,
        code: str,
        message: str,
        node_id: Optional[str] = None,
        detail: Optional[dict] = None,
    ) -> None:
        self.issues.append(
            ValidationIssue(code=code, message=message, node_id=node_id,
                            severity="warning", detail=detail)
        )

    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def merge(self, other: "ValidationResult") -> None:
        """Merge another result's issues into this one."""
        self.issues.extend(other.issues)

    def to_response(self) -> dict:
        """Serialize to the canonical API response shape."""
        if self.is_valid:
            return {
                "valid": True,
                "errors": [],
                "warnings": [w.to_dict() for w in self.warnings],
            }
        return {
            "valid": False,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
        }
