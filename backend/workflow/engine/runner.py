"""
AutoFlow AI X — Workflow Runner
================================
The core runtime engine. Traverses a workflow graph node by node,
manages context propagation, handles retries, and writes audit logs.

Execution model:
  - Iterative DFS from the trigger node (not topological sort)
  - Follows on_success / on_failure / condition edges at runtime
  - Condition nodes evaluate their output["result"] to pick True/False edge
  - Loop nodes iterate their body sub-graph for each item in the list
  - All node I/O is recorded in workflow_run_step_logs for debugging

Retry policy (per node):
  - max_attempts: from node.retry_policy or default (3)
  - backoff: exponential — wait = backoff_seconds * (multiplier ^ attempt)
  - After all attempts exhausted → follow on_failure edge or stop run as FAILED
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from backend.database.models import (
    ExecutionEvent,
    RunStatus,
    WorkflowNode,
    WorkflowRun,
    WorkflowRunStepLog,
)
from backend.workflow.dsl.schema import NodeType, WorkflowDSL, WorkflowNodeDSL
from backend.workflow.engine.context import ExecutionContext
from backend.workflow.engine.credential_resolver import CredentialResolver
from backend.workflow.engine.executors.base import ExecutorResult
from backend.workflow.engine.registry import get_executor
from backend.workflow.event_bus import event_bus

logger = logging.getLogger(__name__)

DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_BACKOFF_SECONDS = 30
DEFAULT_BACKOFF_MULTIPLIER = 2.0
MAX_LOOP_ITERATIONS = 500   # Safety guard against infinite loops
MAX_NODE_VISITS = 1000      # Safety guard against runaway graphs


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class WorkflowRunner:
    """
    Executes a WorkflowDSL graph for a single workflow run.

    Usage:
        runner = WorkflowRunner(dsl=dsl, run_id=run_id, db=db, trigger_payload={...})
        await runner.run()
    """

    def __init__(
        self,
        dsl: WorkflowDSL,
        run_id: uuid.UUID,
        db: Session,
        trigger_payload: dict[str, Any] = None,
        user_id: uuid.UUID = None,
        workflow_id: uuid.UUID = None,
        triggered_by: str = "manual",
    ):
        self.dsl = dsl
        self.run_id = run_id
        self.db = db
        self.user_id = user_id

        # Build a fast lookup map: dsl_node_id → WorkflowNodeDSL
        self._node_map: dict[str, WorkflowNodeDSL] = {n.id: n for n in dsl.nodes}

        # Build edge lookup: source_id → list of edges
        self._edge_map: dict[str, list] = {}
        for edge in dsl.edges:
            self._edge_map.setdefault(edge.source_id, []).append(edge)

        # Execution context — shared across all nodes in this run
        self.context = ExecutionContext(
            run_id=run_id,
            trigger_payload=trigger_payload or {},
            workflow_variables=dsl.variables.copy(),
            db=db,
            user_id=user_id,
            workflow_id=workflow_id,
            triggered_by=triggered_by,
        )

        # CredentialResolver — single point for credential lookup (RFC-001 §8)
        self._credential_resolver = CredentialResolver(db=db)

        # Track visited nodes to prevent infinite loops
        self._visit_count = 0

        # DB node ID lookup: dsl_node_id → db UUID (populated lazily)
        self._db_node_id_map: dict[str, uuid.UUID] = {}

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC ENTRY POINT
    # ─────────────────────────────────────────────────────────────────────────

    async def run(self) -> None:
        """
        Start execution from the trigger node and traverse the graph.
        Updates the WorkflowRun status in the DB at start and completion.
        """
        self._update_run_status(RunStatus.running, started_at=_utcnow())
        event_bus.emit("ExecutionStarted", {
            "run_id": str(self.run_id),
            "workflow_id": self.context.execution_metadata.get("workflow_id"),
            "triggered_by": self.context.execution_metadata.get("triggered_by"),
        })

        try:
            trigger_node = next(
                (n for n in self.dsl.nodes if n.type == NodeType.trigger), None
            )
            if not trigger_node:
                raise RuntimeError("No trigger node found in workflow DSL.")

            logger.info(
                f"[Runner] Starting run {self.run_id} for workflow '{self.dsl.name}'"
            )
            await self._execute_from_node(trigger_node.id)

            # Completed without error
            self._update_run_status(RunStatus.success, finished_at=_utcnow())
            logger.info(f"[Runner] Run {self.run_id} completed successfully.")
            event_bus.emit("ExecutionFinished", {
                "run_id": str(self.run_id),
                "workflow_id": self.context.execution_metadata.get("workflow_id"),
                "status": "success",
            })

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[Runner] Run {self.run_id} FAILED: {error_msg}", exc_info=True)
            self.context.set_error(error_msg)
            self._update_run_status(
                RunStatus.failed,
                finished_at=_utcnow(),
                error_message=error_msg,
            )
            event_bus.emit("ExecutionFinished", {
                "run_id": str(self.run_id),
                "workflow_id": self.context.execution_metadata.get("workflow_id"),
                "status": "failed",
                "error": error_msg,
            })
            raise

    # ─────────────────────────────────────────────────────────────────────────────
    # PUBLIC: EXECUTE SINGLE NODE (Node Inspector Execute Step — RFC-002 §1)
    # ─────────────────────────────────────────────────────────────────────────────

    async def execute_single_node(
        self,
        node: "WorkflowNodeDSL",
        params_override: dict[str, Any] = None,
    ) -> "ExecutorResult":
        """
        Execute one node in isolation — the Node Inspector "Execute Step" path.

        CONTRACT (RFC-002 §1: same pipeline, not a separate code path):
          - Uses the same CredentialResolver → ExecutionContext → Executor chain
            as the full run. No mocks, no special cases.
          - Runs exactly 1 attempt (no retry loop — single-shot by design).
          - Does not write a DB WorkflowRun or WorkflowRunStepLog record
            (ephemeral; the run_id on self.context is a throwaway UUID).
          - Caller (router) is responsible for building the response DTO and
            scrubbing secrets via _scrub_secrets() before returning to client.

        execute_once and always_output_data are no-ops here:
          They apply only to full runs with a persistent run_id.
          This method logs a warning if either is True on the node
          so operators know the setting was seen but not applied.

        Args:
            node            : The DSL node to execute (may be a copy with overridden params).
            params_override : Merged on top of node.params for this call only.
                              Never written back to the DSL.
        """
        if node.execute_once:
            logger.info(
                "[ExecuteStep] node '%s' has execute_once=True — "
                "no-op in Execute Step context (applies to full runs only).",
                node.id,
            )
        if node.always_output_data:
            logger.info(
                "[ExecuteStep] node '%s' has always_output_data=True — "
                "no-op in Execute Step context (applies to full runs only).",
                node.id,
            )

        # Merge param overrides (never persisted)
        effective_params = {**node.params, **(params_override or {})}

        # Resolve template variables against the context
        resolved_params = self.context.resolve_params(effective_params)

        # Resolve credentials — same path as full run (RFC-001 §8)
        self._credential_resolver.resolve_for_node(node, self.context)

        return await self._dispatch_executor(node, resolved_params)

    # ─────────────────────────────────────────────────────────────────────────────
    # GRAPH TRAVERSAL
    # ─────────────────────────────────────────────────────────────────────────────

    async def _execute_from_node(self, node_id: str) -> None:
        """
        Recursively (iteratively via async calls) traverse the graph
        starting from node_id, following edges based on execution results.
        """
        current_id: Optional[str] = node_id

        while current_id is not None:
            self._visit_count += 1
            if self._visit_count > MAX_NODE_VISITS:
                raise RuntimeError(
                    f"Safety limit reached: visited {MAX_NODE_VISITS} nodes. "
                    f"Possible infinite loop in workflow '{self.dsl.name}'."
                )

            node = self._node_map.get(current_id)
            if not node:
                logger.error(f"[Runner] Node '{current_id}' not found in DSL. Stopping.")
                break

            # ── Execute with retry ───────────────────────────────────────────
            result = await self._execute_with_retry(node)

            # ── Determine next node based on node type ───────────────────────
            if node.type == NodeType.condition:
                current_id = self._resolve_condition_next(node, result)

            elif node.type == NodeType.loop:
                # Loop: iterate over items, execute body for each, then stop
                await self._execute_loop(node, result)
                current_id = None  # Loop manages its own chain; stop linear traversal

            else:
                # Standard node: follow on_success or on_failure
                if result.success:
                    current_id = node.on_success
                else:
                    # Failure: follow on_failure if set, otherwise stop the run
                    if node.on_failure:
                        logger.warning(
                            f"[Runner] Node '{node.id}' failed, routing to on_failure: '{node.on_failure}'"
                        )
                        self.context.set_error(result.error or "Unknown error")
                        current_id = node.on_failure
                    else:
                        logger.error(
                            f"[Runner] Node '{node.id}' failed with no on_failure handler. "
                            f"Stopping run. Error: {result.error}"
                        )
                        raise RuntimeError(
                            f"Node '{node.id}' ({node.label}) failed: {result.error}"
                        )

    def _resolve_condition_next(
        self, node: WorkflowNodeDSL, result: ExecutorResult
    ) -> Optional[str]:
        """
        For a condition node, read result.output["result"] (bool) and find the
        matching True/False edge. Falls back to on_success/on_failure.
        """
        condition_result: bool = result.output.get("result", False)
        label_to_match = "true" if condition_result else "false"

        edges = self._edge_map.get(node.id, [])
        for edge in edges:
            if edge.label and edge.label.lower() in (label_to_match, "yes" if condition_result else "no"):
                return edge.target_id

        # Fallback to on_success/on_failure pointers
        if condition_result and node.on_success:
            return node.on_success
        if not condition_result and node.on_failure:
            return node.on_failure

        logger.warning(f"[Runner] Condition node '{node.id}' has no edge for result={condition_result}. Stopping.")
        return None

    async def _execute_loop(
        self, node: WorkflowNodeDSL, setup_result: ExecutorResult
    ) -> None:
        """
        Execute the loop body for each item in the list.
        The body starts at node.on_success and runs until no more on_success.
        """
        items: list = setup_result.output.get("items", [])
        total = len(items)

        if total == 0:
            logger.info(f"[Loop] '{node.label}': 0 items, skipping.")
            return

        if total > MAX_LOOP_ITERATIONS:
            logger.warning(
                f"[Loop] '{node.label}': {total} items exceeds safety limit "
                f"({MAX_LOOP_ITERATIONS}). Truncating."
            )
            items = items[:MAX_LOOP_ITERATIONS]

        body_start = node.on_success
        if not body_start:
            logger.warning(f"[Loop] '{node.label}' has no on_success body node. Skipping.")
            return

        logger.info(f"[Loop] '{node.label}': iterating {len(items)} items")

        for i, item in enumerate(items):
            logger.info(f"[Loop] '{node.label}': iteration {i + 1}/{len(items)}")
            self.context.set_loop_item(item)

            # Execute the body sub-graph for this item
            # We use a temporary visit count reset guard scoped to loop body
            body_visit_start = self._visit_count
            try:
                await self._execute_from_node(body_start)
            except Exception as e:
                logger.error(f"[Loop] Item {i + 1} failed: {e}. Continuing to next item.")
            finally:
                # Reset visit count back to pre-loop value after each iteration
                # (body visits don't compound toward the global limit)
                self._visit_count = body_visit_start

        self.context.clear_loop_item()
        logger.info(f"[Loop] '{node.label}': all iterations complete.")

    # ─────────────────────────────────────────────────────────────────────────
    # NODE EXECUTION WITH RETRY
    # ─────────────────────────────────────────────────────────────────────────

    async def _execute_with_retry(self, node: WorkflowNodeDSL) -> ExecutorResult:
        """
        Execute a single node with exponential backoff retry on failure.
        Writes a step log entry for each attempt.

        Retry policy (in priority order):
          1. node.retry_policy (from DSL)
          2. Defaults (3 attempts, 30s backoff, 2x multiplier)
        """
        if node.is_disabled:
            logger.info(f"[Runner] Skipping disabled node '{node.id}' ({node.label})")
            return ExecutorResult.ok(output={"skipped": True, "reason": "disabled"})

        policy = node.retry_policy
        max_attempts = policy.max_attempts if policy else DEFAULT_MAX_ATTEMPTS
        backoff_secs = policy.backoff_seconds if policy else DEFAULT_BACKOFF_SECONDS
        multiplier = policy.backoff_multiplier if policy else DEFAULT_BACKOFF_MULTIPLIER

        # Resolve template variables in params ONCE before retrying
        resolved_params = self.context.resolve_params(node.params)

        # Resolve credentials for this node (RFC-001 §8)
        # Populates context.get_secret(service_name) before dispatch.
        self._credential_resolver.resolve_for_node(node, self.context)

        last_result: Optional[ExecutorResult] = None

        for attempt in range(1, max_attempts + 1):
            step_log_id = uuid.uuid4()
            started_at = _utcnow()

            try:
                result = await self._dispatch_executor(node, resolved_params)
                finished_at = _utcnow()
                duration_ms = int((finished_at - started_at).total_seconds() * 1000)

                # Write step log
                self._write_step_log(
                    step_log_id=step_log_id,
                    node_dsl_id=node.id,
                    status=RunStatus.success if result.success else RunStatus.failed,
                    input_json=resolved_params,
                    output_json=result.output,
                    error_message=result.error,
                    started_at=started_at,
                    finished_at=finished_at,
                    duration_ms=duration_ms,
                )

                if result.success:
                    # Store output in context for downstream nodes
                    self.context.set_node_output(node.id, result.output)
                    return result

                # Failed but not an exception — check if we should retry
                last_result = result
                logger.warning(
                    f"[Runner] Node '{node.id}' attempt {attempt}/{max_attempts} "
                    f"returned failure: {result.error}"
                )

            except Exception as exc:
                finished_at = _utcnow()
                duration_ms = int((finished_at - started_at).total_seconds() * 1000)
                error_msg = str(exc)

                self._write_step_log(
                    step_log_id=step_log_id,
                    node_dsl_id=node.id,
                    status=RunStatus.failed,
                    input_json=resolved_params,
                    output_json={},
                    error_message=error_msg,
                    started_at=started_at,
                    finished_at=finished_at,
                    duration_ms=duration_ms,
                )

                last_result = ExecutorResult.fail(error_msg)
                logger.error(
                    f"[Runner] Node '{node.id}' attempt {attempt}/{max_attempts} "
                    f"raised exception: {exc}"
                )

            # Wait before retrying (exponential backoff)
            if attempt < max_attempts:
                wait_time = backoff_secs * (multiplier ** (attempt - 1))
                logger.info(
                    f"[Runner] Retrying node '{node.id}' in {wait_time:.0f}s "
                    f"(attempt {attempt + 1}/{max_attempts})"
                )
                self._update_run_status(RunStatus.retrying)
                await asyncio.sleep(wait_time)

        # All attempts exhausted
        logger.error(
            f"[Runner] Node '{node.id}' ({node.label}) failed after "
            f"{max_attempts} attempts. Last error: {last_result.error if last_result else 'unknown'}"
        )
        event_bus.emit("NodeFailed", {
            "run_id": str(self.run_id),
            "node_id": node.id,
            "node_label": node.label,
            "error": last_result.error if last_result else "Max retry attempts exhausted.",
            "attempts": max_attempts,
        })
        return last_result or ExecutorResult.fail("Max retry attempts exhausted.")

    async def _dispatch_executor(
        self, node: WorkflowNodeDSL, resolved_params: dict[str, Any]
    ) -> ExecutorResult:
        """Look up the correct executor and run it."""
        executor = get_executor(node.service.value, node.operation.value)

        if executor is None:
            return ExecutorResult.fail(
                f"No executor found for '{node.service.value}.{node.operation.value}'. "
                f"This integration may not be implemented yet."
            )

        logger.info(
            f"[Runner] Executing '{node.id}' ({node.label}) "
            f"via {executor.__class__.__name__}"
        )
        return await executor.execute(node, self.context, resolved_params)

    # ─────────────────────────────────────────────────────────────────────────
    # DATABASE WRITES
    # ─────────────────────────────────────────────────────────────────────────


    def _emit_event(self, event_type: str, node_id: Optional[str] = None, payload: Optional[dict] = None) -> None:
        """Append an event to the durable execution ledger."""
        if not hasattr(self, "db") or self.db is None:
            return

        # safely convert UUID string to UUID if needed, but ExecutionEvent accepts standard formats
        event = ExecutionEvent(
            run_id=self.run_id,
            node_id=node_id,
            event_type=event_type,
            payload=payload or {}
        )
        self.db.add(event)
        self.db.commit()

    def _update_run_status(
        self,
        status: RunStatus,
        started_at: Optional[datetime] = None,
        finished_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update the WorkflowRun record in the database."""
        try:
            # Always ensure the session is in a clean state before querying.
            # If a previous commit failed and was rolled back, the session may
            # still hold stale pending state that causes SQLAlchemy to evaluate
            # constraint expressions (e.g. CheckConstraint strings) as Python,
            # leading to NameError: name 'node_id' is not defined.
            try:
                self.db.rollback()
            except Exception:
                pass

            run = self.db.query(WorkflowRun).filter(WorkflowRun.id == self.run_id).first()
            if not run:
                logger.error(f"[Runner] WorkflowRun {self.run_id} not found in DB.")
                return

            run.status = status.value
            if started_at:
                run.started_at = started_at
            if finished_at:
                run.finished_at = finished_at
                if run.started_at:
                    run.duration_ms = int(
                        (finished_at - run.started_at).total_seconds() * 1000
                    )
            if error_message:
                run.error_message = error_message[:2000]  # Clamp to column limit

            self.db.commit()
            self._emit_event(f'NODE_{status.name.upper()}', node_id=node_id, payload={"error": error_message, "duration": duration_ms})
            self._emit_event(f'RUN_{status.name.upper()}', payload={"error": error_message, "duration": self.context.get("duration_ms")})
        except Exception as e:
            logger.error(f"[Runner] Failed to update run status: {e}")
            try:
                self.db.rollback()
            except Exception:
                pass

    def _write_step_log(
        self,
        step_log_id: uuid.UUID,
        node_dsl_id: str,
        status: RunStatus,
        input_json: dict,
        output_json: dict,
        error_message: Optional[str],
        started_at: datetime,
        finished_at: datetime,
        duration_ms: int,
    ) -> None:
        """
        Write a WorkflowRunStepLog entry for a single node execution attempt.
        The node_dsl_id is mapped to the DB node UUID via the config_json field.
        """
        try:
            # Always ensure the session is in a clean state before querying.
            # If a previous commit failed, the session may hold stale pending state
            # that causes SQLAlchemy to evaluate CheckConstraint strings as Python,
            # producing NameError: name 'node_id' is not defined.
            try:
                self.db.rollback()
            except Exception:
                pass

            # Find the DB WorkflowNode matching this DSL node ID
            db_node = (
                self.db.query(WorkflowNode)
                .filter(
                    WorkflowNode.workflow_id == self._get_workflow_id(),
                    WorkflowNode.config_json["dsl_id"].astext == node_dsl_id,
                )
                .first()
            )

            if not db_node:
                logger.warning(f"[Runner] DB node not found for dsl_id='{node_dsl_id}'. Skipping step log.")
                return

            step_log = WorkflowRunStepLog(
                id=step_log_id,
                run_id=self.run_id,
                node_id=db_node.id,
                status=status.value,
                input_json=input_json,
                output_json=output_json,
                error_message=(error_message[:2000] if error_message else None),
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=duration_ms,
            )
            self.db.add(step_log)
            self.db.commit()
            self._emit_event(f'NODE_{status.name.upper()}', node_id=node_id, payload={"error": error_message, "duration": duration_ms})
            self._emit_event(f'RUN_{status.name.upper()}', payload={"error": error_message, "duration": self.context.get("duration_ms")})

        except Exception as e:
            logger.error(f"[Runner] Failed to write step log for node '{node_dsl_id}': {e}")
            try:
                self.db.rollback()
            except Exception:
                pass

    def _get_workflow_id(self) -> Optional[uuid.UUID]:
        """Get the workflow_id from the run record."""
        try:
            # Use a clean session state to avoid stale-transaction errors.
            try:
                self.db.rollback()
            except Exception:
                pass
            run = self.db.query(WorkflowRun).filter(WorkflowRun.id == self.run_id).first()
            return run.workflow_id if run else None
        except Exception:
            return None
