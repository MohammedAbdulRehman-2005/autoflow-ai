"""
AutoFlow AI X — Validator API Schemas
"""

import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ValidateWorkflowRequest(BaseModel):
    """
    Request body for POST /workflows/validate.
    Accepts raw DSL JSON (same format as the planner outputs).
    """
    dsl: Dict[str, Any]
    workflow_id: Optional[uuid.UUID] = None  # Pass when updating an existing workflow


class ValidationIssueOut(BaseModel):
    code: str
    message: str
    node_id: Optional[str] = None
    severity: str
    detail: Optional[Dict[str, Any]] = None


class ValidateWorkflowResponse(BaseModel):
    valid: bool
    errors: List[ValidationIssueOut]
    warnings: List[ValidationIssueOut]
    summary: str
