"""
AutoFlow AI X — Executor Base Class
=====================================
All integration executors inherit from BaseExecutor.
Each executor must implement execute() and return an ExecutorResult.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from backend.workflow.dsl.schema import WorkflowNodeDSL
from backend.workflow.engine.context import ExecutionContext

logger = logging.getLogger(__name__)


@dataclass
class ExecutorResult:
    """
    The output of a single node execution.
    
    - success: whether the node completed without error
    - output: dict of output values made available to downstream nodes
    - error: error message if failed
    - metadata: extra data for debugging (request/response details, etc.)
    """
    success: bool
    output: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, output: dict[str, Any] = None, **kwargs) -> "ExecutorResult":
        return cls(success=True, output=output or kwargs)

    @classmethod
    def fail(cls, error: str, output: dict[str, Any] = None) -> "ExecutorResult":
        return cls(success=False, output=output or {}, error=error)


class BaseExecutor(ABC):
    """
    Abstract base class for all AutoFlow integration executors.

    Subclasses implement execute() for a specific service+operation pair.
    The runner calls execute() and handles retry/error logic externally.
    """

    @abstractmethod
    async def execute(
        self,
        node: WorkflowNodeDSL,
        context: ExecutionContext,
        resolved_params: dict[str, Any],
    ) -> ExecutorResult:
        """
        Execute the node's operation.

        Args:
            node: The DSL node definition (type, service, operation, etc.)
            context: The current execution context (for reading previous outputs)
            resolved_params: node.params with all template variables already resolved

        Returns:
            ExecutorResult with success=True and output dict, or success=False with error.
        """

    @property
    def name(self) -> str:
        return self.__class__.__name__
