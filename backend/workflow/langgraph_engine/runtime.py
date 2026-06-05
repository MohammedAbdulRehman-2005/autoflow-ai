"""
AutoFlow AI X — LangGraph Runtime
=====================================
The LangGraph runtime is the execution layer that:
  1. Compiles a DSL → LangGraph StateGraph (via graph_builder.py)
  2. Runs the compiled graph with ainvoke()
  3. Writes per-node step logs back to the PostgreSQL DB
  4. Updates WorkflowRun status just like the simple WorkflowRunner

Backward compatibility:
  - If compile_dsl_to_graph() returns None (no agent nodes), this runtime
    falls back to the existing WorkflowRunner automatically.
  - The Celery task (run_workflow_task) calls this runtime transparently.

Usage:
    runtime = LangGraphRuntime(dsl=dsl, run_id=run_id, db=db, trigger_payload={})
    await runtime.run()
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from backend.database.models import (
    RunStatus,
    WorkflowRun,
    WorkflowRunStepLog,
    WorkflowNode,
)
from backend.workflow.dsl.schema import WorkflowDSL
from backend.workflow.engine.runner import WorkflowRunner
from backend.workflow.langgraph_engine.graph_builder import compile_dsl_to_graph
from backend.workflow.langgraph_engine.state import make_initial_state

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LangGraphRuntime:
    """
    Drop-in replacement for WorkflowRunner that uses LangGraph for agent workflows.

    For non-agent workflows it transparently delegates to WorkflowRunner.
    """

    def __init__(
        self,
        dsl:             WorkflowDSL,
        run_id:          uuid.UUID,
        db:              Session,
        trigger_payload: dict[str, Any] = None,
    ):
        self.dsl             = dsl
        self.run_id          = run_id
        self.db              = db
        self.trigger_payload = trigger_payload or {}

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC ENTRY POINT
    # ─────────────────────────────────────────────────────────────────────────

    async def run(self) -> None:
        """
        Execute the workflow. Automatically picks:
          - LangGraph runtime  → if workflow has ai_agent nodes
          - WorkflowRunner     → if workflow has only simple executor nodes
        """
        # ── Try to compile to LangGraph ──────────────────────────────────────
        try:
            compiled_graph = compile_dsl_to_graph(self.dsl)
        except Exception as e:
            logger.error(f"[LangGraphRuntime] Graph compilation failed: {e}. Falling back to WorkflowRunner.")
            compiled_graph = None

        if compiled_graph is None:
            # ── Fallback: simple executor ────────────────────────────────────
            logger.info(f"[LangGraphRuntime] Run {self.run_id}: using WorkflowRunner (no agent nodes).")
            runner = WorkflowRunner(
                dsl             = self.dsl,
                run_id          = self.run_id,
                db              = self.db,
                trigger_payload = self.trigger_payload,
            )
            await runner.run()
            return

        # ── LangGraph execution ───────────────────────────────────────────────
        logger.info(f"[LangGraphRuntime] Run {self.run_id}: using LangGraph agent runtime.")
        self._update_run_status(RunStatus.running, started_at=_utcnow())

        try:
            trigger_node = next(n for n in self.dsl.nodes if n.type.value == "trigger")
            initial_state = make_initial_state(
                run_id          = str(self.run_id),
                workflow_id     = self.dsl.id,
                workflow_name   = self.dsl.name,
                trigger_payload = self.trigger_payload,
                trigger_node_id = trigger_node.id,
            )

            # ── ainvoke the compiled graph ────────────────────────────────────
            final_state = await compiled_graph.ainvoke(
                initial_state,
                config={"recursion_limit": 50},
            )

            # ── Persist step logs to DB ───────────────────────────────────────
            run_history = final_state.get("run_history", [])
            for step in run_history:
                self._write_step_log_from_record(step)

            # ── Determine final status ────────────────────────────────────────
            if final_state.get("error_state"):
                err = final_state["error_state"]
                self._update_run_status(
                    RunStatus.failed,
                    finished_at   = _utcnow(),
                    error_message = err,
                )
                logger.error(f"[LangGraphRuntime] Run {self.run_id} FAILED: {err}")
            else:
                self._update_run_status(RunStatus.success, finished_at=_utcnow())
                logger.info(f"[LangGraphRuntime] Run {self.run_id} completed successfully "
                            f"({len(run_history)} steps).")

        except Exception as e:
            err = str(e)
            logger.error(f"[LangGraphRuntime] Run {self.run_id} crashed: {err}", exc_info=True)
            self._update_run_status(
                RunStatus.failed,
                finished_at   = _utcnow(),
                error_message = err,
            )
            raise

    # ─────────────────────────────────────────────────────────────────────────
    # DB WRITES
    # ─────────────────────────────────────────────────────────────────────────

    def _update_run_status(
        self,
        status:        RunStatus,
        started_at:    Optional[datetime] = None,
        finished_at:   Optional[datetime] = None,
        error_message: Optional[str]      = None,
    ) -> None:
        try:
            run = self.db.query(WorkflowRun).filter(WorkflowRun.id == self.run_id).first()
            if not run:
                return
            run.status = status.value
            if started_at:  run.started_at  = started_at
            if finished_at:
                run.finished_at = finished_at
                if run.started_at:
                    run.duration_ms = int((finished_at - run.started_at).total_seconds() * 1000)
            if error_message:
                run.error_message = error_message[:2000]
            self.db.commit()
        except Exception as e:
            logger.error(f"[LangGraphRuntime] Failed to update run status: {e}")
            try: self.db.rollback()
            except Exception: pass

    def _write_step_log_from_record(self, step: dict) -> None:
        """Persist one StepRecord from run_history to workflow_run_step_logs."""
        try:
            workflow_id = self._get_workflow_id()
            node_dsl_id = step.get("node_id", "")

            # Skip terminal pseudo-nodes
            if node_dsl_id.startswith("__"):
                return

            # Find the matching DB WorkflowNode
            db_node = None
            if workflow_id:
                db_node = (
                    self.db.query(WorkflowNode)
                    .filter(
                        WorkflowNode.workflow_id == workflow_id,
                        WorkflowNode.config_json["dsl_id"].astext == node_dsl_id,
                    )
                    .first()
                )

            if not db_node:
                logger.debug(f"[LangGraphRuntime] No DB node for dsl_id='{node_dsl_id}'. Skipping step log.")
                return

            # Parse timestamps
            def _parse_dt(s):
                try: return datetime.fromisoformat(s)
                except Exception: return _utcnow()

            started_at  = _parse_dt(step.get("started_at", ""))
            ended_at    = _parse_dt(step.get("ended_at", ""))
            duration_ms = step.get("duration_ms", 0)

            status_value = step.get("status", "success")
            db_status    = RunStatus.success.value if status_value == "success" else RunStatus.failed.value

            log = WorkflowRunStepLog(
                id            = uuid.uuid4(),
                run_id        = self.run_id,
                node_id       = db_node.id,
                status        = db_status,
                input_json    = {},
                output_json   = step.get("output", {}),
                error_message = (step.get("error") or "")[:2000] or None,
                started_at    = started_at,
                finished_at   = ended_at,
                duration_ms   = duration_ms,
            )
            self.db.add(log)
            self.db.commit()
        except Exception as e:
            logger.error(f"[LangGraphRuntime] Failed to write step log: {e}")
            try: self.db.rollback()
            except Exception: pass

    def _get_workflow_id(self) -> Optional[uuid.UUID]:
        try:
            run = self.db.query(WorkflowRun).filter(WorkflowRun.id == self.run_id).first()
            return run.workflow_id if run else None
        except Exception:
            return None
