"""
AutoFlow AI X — Scheduler Service
=====================================
Wraps APScheduler's AsyncIOScheduler with AutoFlow-specific logic:

  - Persists all jobs to PostgreSQL (via SQLAlchemyJobStore) so they
    survive server restarts without re-registration.
  - On startup: scans the `workflows` table and ensures all active
    scheduled workflows have a running APScheduler job.
  - Provides schedule/unschedule/list operations used by the API router.

Supported trigger types:
  1. cron     — "0 9 * * 1" (every Monday at 9am)
  2. interval — every N minutes / hours / days
  3. date     — one-time execution at a specific datetime

Thread safety: AsyncIOScheduler runs in the same event loop as FastAPI.
All public methods are synchronous (scheduler operations are thread-safe);
the job function itself is async.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.database.models import Workflow, WorkflowStatus
from backend.scheduler.jobs import execute_scheduled_workflow
from backend.scheduler.schemas import (
    CronSchedule,
    IntervalSchedule,
    OnceSchedule,
    ScheduleResponse,
    ScheduledWorkflow,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# Naming convention for APScheduler job IDs
_JOB_PREFIX = "autoflow:workflow:"


def _job_id(workflow_id: uuid.UUID) -> str:
    return f"{_JOB_PREFIX}{workflow_id}"


def _workflow_id_from_job(job_id: str) -> Optional[str]:
    if job_id.startswith(_JOB_PREFIX):
        return job_id[len(_JOB_PREFIX):]
    return None


class SchedulerService:
    """
    Singleton service managing the APScheduler instance.
    Initialized once in main.py lifespan and shared via module-level reference.
    """

    def __init__(self) -> None:
        self._scheduler: Optional[AsyncIOScheduler] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def init(self) -> None:
        """
        Configure APScheduler with:
          - SQLAlchemyJobStore → persists jobs to postgres `apscheduler_jobs` table
          - AsyncIOExecutor    → jobs run as async coroutines in FastAPI's event loop
          - coalesce=True      → if server was down, only run missed job once (not N times)
          - misfire_grace_time → allow 60-second late firing before dropping a job
        """
        jobstores = {
            "default": SQLAlchemyJobStore(
                url=settings.DATABASE_URL,
                tablename="apscheduler_jobs",
            )
        }
        executors = {"default": AsyncIOExecutor()}
        job_defaults = {
            "coalesce": True,
            "max_instances": 1,        # Never run the same workflow twice concurrently
            "misfire_grace_time": 60,  # Fire up to 60s late, then skip
        }

        self._scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone="UTC",
        )
        logger.info("[Scheduler] APScheduler configured with SQLAlchemy job store.")

    async def start(self, db: Session) -> None:
        """
        Start the scheduler and reconcile DB workflows with job store.

        Reconciliation logic:
          - For each active scheduled workflow in DB:
              If job exists in store → leave it (APScheduler restored it from DB)
              If job missing         → re-register it (handles fresh deployments
                                       or DB migrations that cleared the job store)
        """
        if not self._scheduler:
            raise RuntimeError("SchedulerService.init() must be called before start().")

        self._scheduler.start()
        logger.info("[Scheduler] APScheduler started.")

        await self._reconcile_with_db(db)

    async def shutdown(self) -> None:
        """Gracefully stop the scheduler on app shutdown."""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("[Scheduler] APScheduler stopped.")

    async def _reconcile_with_db(self, db: Session) -> None:
        """
        Ensure all active workflows with cron schedules have APScheduler jobs.
        Called on startup to handle cases where the job store was cleared.
        """
        active_workflows = (
            db.query(Workflow)
            .filter(
                Workflow.status == WorkflowStatus.active,
                Workflow.cron_expression.isnot(None),
                Workflow.deleted_at.is_(None),
            )
            .all()
        )

        registered = 0
        skipped = 0

        for wf in active_workflows:
            job_id = _job_id(wf.id)
            existing_job = self._scheduler.get_job(job_id)

            if existing_job:
                # Job store already has it — APScheduler restored state from DB
                skipped += 1
                logger.debug(
                    f"[Scheduler] Job already registered for workflow '{wf.name}' "
                    f"(next run: {existing_job.next_run_time})"
                )
            else:
                # Missing — register now
                try:
                    self._add_cron_job(
                        workflow_id=wf.id,
                        cron_expr=wf.cron_expression,
                        timezone=wf.timezone or "UTC",
                    )
                    registered += 1
                    logger.info(
                        f"[Scheduler] Reconciled: registered cron job for workflow '{wf.name}'"
                    )
                except Exception as e:
                    logger.error(
                        f"[Scheduler] Failed to reconcile workflow '{wf.name}' ({wf.id}): {e}"
                    )

        logger.info(
            f"[Scheduler] Startup reconciliation complete: "
            f"{registered} registered, {skipped} already present, "
            f"{len(active_workflows)} total scheduled workflows."
        )

    # ── Internal Job Registration ─────────────────────────────────────────────

    def _add_cron_job(
        self,
        workflow_id: uuid.UUID,
        cron_expr: str,
        timezone: str = "UTC",
    ) -> datetime:
        """Register a cron APScheduler job. Returns the next run time."""
        parts = cron_expr.strip().split()
        if len(parts) not in (5, 6):
            raise ValueError(f"Invalid cron expression '{cron_expr}': expected 5 or 6 fields.")

        minute, hour, day, month, day_of_week = parts[:5]
        second = parts[5] if len(parts) == 6 else "0"

        job = self._scheduler.add_job(
            func=execute_scheduled_workflow,
            trigger=CronTrigger(
                second=second,
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
                timezone=timezone,
            ),
            id=_job_id(workflow_id),
            args=[str(workflow_id)],
            replace_existing=True,
            name=f"workflow:{workflow_id}",
        )
        return job.next_run_time

    def _add_interval_job(
        self,
        workflow_id: uuid.UUID,
        every_n_minutes: Optional[int] = None,
        every_n_hours: Optional[int] = None,
        every_n_days: Optional[int] = None,
        start_date: Optional[datetime] = None,
        timezone: str = "UTC",
    ) -> datetime:
        """Register an interval APScheduler job. Returns the next run time."""
        kwargs = {}
        if every_n_minutes:
            kwargs["minutes"] = every_n_minutes
        if every_n_hours:
            kwargs["hours"] = every_n_hours
        if every_n_days:
            kwargs["days"] = every_n_days

        job = self._scheduler.add_job(
            func=execute_scheduled_workflow,
            trigger=IntervalTrigger(
                **kwargs,
                start_date=start_date or datetime.now(timezone if isinstance(timezone, object) else timezone),
                timezone=timezone,
            ),
            id=_job_id(workflow_id),
            args=[str(workflow_id)],
            replace_existing=True,
            name=f"workflow:{workflow_id}",
        )
        return job.next_run_time

    def _add_date_job(
        self,
        workflow_id: uuid.UUID,
        run_at: datetime,
    ) -> datetime:
        """Register a one-time date APScheduler job. Returns the run time."""
        job = self._scheduler.add_job(
            func=execute_scheduled_workflow,
            trigger=DateTrigger(run_date=run_at),
            id=_job_id(workflow_id),
            args=[str(workflow_id)],
            replace_existing=True,
            name=f"workflow:{workflow_id}",
        )
        return job.next_run_time

    # ── Public API Operations ─────────────────────────────────────────────────

    def schedule_workflow(
        self,
        workflow: Workflow,
        request,  # CronSchedule | IntervalSchedule | OnceSchedule
        db: Session,
    ) -> ScheduleResponse:
        """
        Create or update the schedule for a workflow.
        Updates workflow.cron_expression in DB and registers/replaces the APScheduler job.
        """
        trigger_type = request.trigger_type

        if trigger_type == "cron":
            # Persist to DB
            workflow.cron_expression = request.cron
            workflow.timezone = request.timezone
            db.commit()

            next_run = self._add_cron_job(
                workflow_id=workflow.id,
                cron_expr=request.cron,
                timezone=request.timezone,
            )
            display = f"cron '{request.cron}' ({request.timezone})"

        elif trigger_type == "interval":
            # Store a synthetic cron-like description in cron_expression
            desc_parts = []
            if request.every_n_minutes:
                desc_parts.append(f"every {request.every_n_minutes}m")
            if request.every_n_hours:
                desc_parts.append(f"every {request.every_n_hours}h")
            if request.every_n_days:
                desc_parts.append(f"every {request.every_n_days}d")
            workflow.cron_expression = f"interval:{','.join(desc_parts)}"
            workflow.timezone = request.timezone
            db.commit()

            next_run = self._add_interval_job(
                workflow_id=workflow.id,
                every_n_minutes=request.every_n_minutes,
                every_n_hours=request.every_n_hours,
                every_n_days=request.every_n_days,
                start_date=request.start_date,
                timezone=request.timezone,
            )
            display = f"interval {workflow.cron_expression}"

        elif trigger_type == "date":
            workflow.cron_expression = f"once:{request.run_at.isoformat()}"
            workflow.timezone = "UTC"
            db.commit()

            next_run = self._add_date_job(
                workflow_id=workflow.id,
                run_at=request.run_at,
            )
            display = f"one-time at {request.run_at.isoformat()}"

        else:
            raise ValueError(f"Unknown trigger type: {trigger_type}")

        job_id = _job_id(workflow.id)
        logger.info(
            f"[Scheduler] Scheduled workflow '{workflow.name}' "
            f"({workflow.id}) with {display}. Next run: {next_run}"
        )

        return ScheduleResponse(
            workflow_id=workflow.id,
            job_id=job_id,
            trigger_type=trigger_type,
            next_run_time=next_run,
            message=f"Workflow scheduled with {display}.",
        )

    def unschedule_workflow(self, workflow: Workflow, db: Session) -> None:
        """
        Remove the APScheduler job and clear the cron_expression in DB.
        Idempotent — does not raise if no job exists.
        """
        job_id = _job_id(workflow.id)
        existing = self._scheduler.get_job(job_id)
        if existing:
            self._scheduler.remove_job(job_id)
            logger.info(
                f"[Scheduler] Removed job '{job_id}' for workflow '{workflow.name}'"
            )
        else:
            logger.debug(f"[Scheduler] No job found for '{job_id}' — nothing to remove.")

        # Clear cron_expression from DB
        workflow.cron_expression = None
        db.commit()

    def list_scheduled(self, db: Session) -> list[ScheduledWorkflow]:
        """
        Returns all currently scheduled workflows, cross-referencing the
        APScheduler job list with workflow metadata from the DB.
        """
        all_jobs = self._scheduler.get_jobs()
        results: list[ScheduledWorkflow] = []

        for job in all_jobs:
            wf_id_str = _workflow_id_from_job(job.id)
            if not wf_id_str:
                continue

            try:
                wf_id = uuid.UUID(wf_id_str)
            except ValueError:
                continue

            wf = db.query(Workflow).filter(Workflow.id == wf_id).first()
            if not wf:
                continue

            # Determine trigger type from stored cron_expression
            cron_expr = wf.cron_expression or ""
            if cron_expr.startswith("interval:"):
                trigger_type = "interval"
            elif cron_expr.startswith("once:"):
                trigger_type = "date"
            else:
                trigger_type = "cron"

            results.append(
                ScheduledWorkflow(
                    workflow_id=wf.id,
                    workflow_name=wf.name,
                    status=wf.status,
                    trigger_type=trigger_type,
                    cron_expression=cron_expr if trigger_type == "cron" else None,
                    timezone=wf.timezone or "UTC",
                    next_run_time=job.next_run_time,
                    job_id=job.id,
                )
            )

        return results

    def get_next_run_time(self, workflow_id: uuid.UUID) -> Optional[datetime]:
        """Get the next scheduled run time for a workflow, or None if not scheduled."""
        job = self._scheduler.get_job(_job_id(workflow_id))
        return job.next_run_time if job else None

    def pause_workflow(self, workflow_id: uuid.UUID) -> None:
        """Pause a scheduled job without removing it."""
        job_id = _job_id(workflow_id)
        if self._scheduler.get_job(job_id):
            self._scheduler.pause_job(job_id)
            logger.info(f"[Scheduler] Paused job '{job_id}'")

    def resume_workflow(self, workflow_id: uuid.UUID) -> None:
        """Resume a previously paused scheduled job."""
        job_id = _job_id(workflow_id)
        if self._scheduler.get_job(job_id):
            self._scheduler.resume_job(job_id)
            logger.info(f"[Scheduler] Resumed job '{job_id}'")

    @property
    def is_running(self) -> bool:
        return bool(self._scheduler and self._scheduler.running)


# ── Module-level singleton ────────────────────────────────────────────────────
# Imported by main.py lifespan AND the router.
# Single instance shared across the entire application.

scheduler_service = SchedulerService()
