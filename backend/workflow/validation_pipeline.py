"""
AutoFlow AI X — Backend Validation Pipeline  (Sprint 3.5, Goal 6)
==================================================================
A composable, layered validation pipeline for DSL mutations.

Every editor action that modifies the workflow DSL is expected to run
this pipeline before persisting changes. The pipeline runs stages
sequentially; any stage can add errors or warnings to the context.

Stages (in order):
  1. UIValidationStage     — field-level checks (required, type coercion)
  2. SchemaValidationStage — Pydantic WorkflowDSL parse
  3. BusinessValidationStage — graph rules (cycle, reachability) via validator.py

Usage::

    from backend.workflow.validation_pipeline import ValidationPipeline, default_pipeline

    result = default_pipeline().run(raw_dsl_dict)
    if not result.is_valid:
        raise HTTPException(422, result.errors)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ─── Context passed between stages ───────────────────────────────────────────

@dataclass
class ValidationContext:
    """
    Shared context object that flows through each pipeline stage.

    A stage reads from raw_input or parsed_dsl, appends to errors/warnings,
    and may set parsed_dsl for the next stage to consume.
    """
    raw_input: Dict[str, Any]
    parsed_dsl: Optional[Any] = None   # WorkflowDSL once parsed by SchemaValidationStage
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)


# ─── Validation result (same shape as dsl/validator.py ValidationResult) ─────

@dataclass
class PipelineValidationResult:
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {'is_valid': self.is_valid, 'errors': self.errors, 'warnings': self.warnings}


# ─── Abstract stage ───────────────────────────────────────────────────────────

class ValidationStage(ABC):
    """
    A single, composable validation step.

    Implementations must not raise exceptions for validation failures —
    they should append to ctx.errors. Unexpected exceptions are allowed
    to propagate (they indicate bugs, not validation failures).
    """

    @abstractmethod
    def run(self, ctx: ValidationContext) -> ValidationContext:
        """Run the stage. Mutate ctx in place, return it."""
        ...

    @property
    def name(self) -> str:
        return self.__class__.__name__


# ─── Stage 1: UI Validation ───────────────────────────────────────────────────

class UIValidationStage(ValidationStage):
    """
    Field-level checks that can be evaluated without Pydantic.

    Currently checks:
    - DSL is a dict (not None, not a list)
    - 'name' field is a non-empty string
    - 'nodes' is a list
    - 'edges' is a list
    """

    def run(self, ctx: ValidationContext) -> ValidationContext:
        raw = ctx.raw_input

        if not isinstance(raw, dict):
            ctx.add_error('DSL must be a JSON object, not a primitive or list.')
            return ctx  # No point running further checks

        name = raw.get('name', '')
        if not isinstance(name, str) or not name.strip():
            ctx.add_error('Workflow name is required and must be a non-empty string.')

        nodes = raw.get('nodes')
        if nodes is not None and not isinstance(nodes, list):
            ctx.add_error("'nodes' must be a list.")

        edges = raw.get('edges')
        if edges is not None and not isinstance(edges, list):
            ctx.add_error("'edges' must be a list.")

        return ctx


# ─── Stage 2: Schema Validation ───────────────────────────────────────────────

class SchemaValidationStage(ValidationStage):
    """
    Validates raw_input against the WorkflowDSL Pydantic schema.

    On success: sets ctx.parsed_dsl to the parsed WorkflowDSL object.
    On failure: appends each Pydantic validation error as a ctx error.
    """

    def run(self, ctx: ValidationContext) -> ValidationContext:
        if not ctx.is_valid:
            # Skip schema validation if UI checks already failed
            return ctx

        try:
            from backend.workflow.dsl.schema import WorkflowDSL
            ctx.parsed_dsl = WorkflowDSL(**ctx.raw_input)
        except Exception as exc:
            # Pydantic ValidationError has a .errors() method; others are plain exceptions
            if hasattr(exc, 'errors'):
                for err in exc.errors():
                    loc = ' → '.join(str(x) for x in err.get('loc', []))
                    msg = err.get('msg', str(err))
                    ctx.add_error(f'Schema [{loc}]: {msg}')
            else:
                ctx.add_error(f'Schema validation error: {exc}')

        return ctx


# ─── Stage 3: Business Validation ────────────────────────────────────────────

class BusinessValidationStage(ValidationStage):
    """
    Graph-level semantic checks: cycle detection, reachability, condition
    integrity, loop structure. Delegates to the existing validator.py.

    Requires ctx.parsed_dsl to be set (i.e. SchemaValidationStage must
    have run and succeeded first).
    """

    def run(self, ctx: ValidationContext) -> ValidationContext:
        if not ctx.is_valid or ctx.parsed_dsl is None:
            return ctx  # Can't run without a valid parsed DSL

        try:
            from backend.workflow.dsl.validator import validate_workflow_graph
            result = validate_workflow_graph(ctx.parsed_dsl)
            for err in result.errors:
                ctx.add_error(err)
            for warn in result.warnings:
                ctx.add_warning(warn)
        except Exception as exc:
            ctx.add_error(f'Business validation error: {exc}')

        return ctx


# ─── Pipeline ─────────────────────────────────────────────────────────────────

class ValidationPipeline:
    """
    Runs a sequence of ValidationStage instances against a raw DSL dict.

    Stages are run in order. A stage that adds errors does NOT stop the
    pipeline unless it explicitly returns early (see UIValidationStage).
    This allows collecting all errors in one pass.
    """

    def __init__(self, stages: List[ValidationStage]) -> None:
        self._stages = stages

    def run(self, raw_dsl: Dict[str, Any]) -> PipelineValidationResult:
        """
        Run all stages against raw_dsl.

        Returns a PipelineValidationResult with is_valid=True only if
        no stage added errors.
        """
        ctx = ValidationContext(raw_input=raw_dsl)
        for stage in self._stages:
            ctx = stage.run(ctx)
        return PipelineValidationResult(
            is_valid=ctx.is_valid,
            errors=ctx.errors,
            warnings=ctx.warnings,
        )


def default_pipeline() -> ValidationPipeline:
    """
    Construct the standard three-stage pipeline.

    Use this factory in production code; inject custom stages in tests.
    """
    return ValidationPipeline([
        UIValidationStage(),
        SchemaValidationStage(),
        BusinessValidationStage(),
    ])
