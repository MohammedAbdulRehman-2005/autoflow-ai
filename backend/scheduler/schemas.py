"""
AutoFlow AI X — Scheduler API Schemas
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, model_validator


# ─────────────────────────────────────────────────────────────────────────────
# SCHEDULE REQUEST — supports 3 trigger types
# ─────────────────────────────────────────────────────────────────────────────

class CronSchedule(BaseModel):
    trigger_type: Literal["cron"]
    cron: str = Field(
        ...,
        description="Standard 5-field cron expression. E.g. '0 9 * * 1' = Mon 9am",
        examples=["0 9 * * *", "0 8 * * 1", "*/30 * * * *"],
    )
    timezone: str = Field(default="UTC", description="IANA timezone. E.g. 'Asia/Kolkata'")


class IntervalSchedule(BaseModel):
    trigger_type: Literal["interval"]
    every_n_minutes: Optional[int] = Field(None, ge=1, description="Run every N minutes")
    every_n_hours: Optional[int] = Field(None, ge=1, description="Run every N hours")
    every_n_days: Optional[int] = Field(None, ge=1, description="Run every N days")
    start_date: Optional[datetime] = Field(None, description="When to start the interval")
    timezone: str = Field(default="UTC")

    @model_validator(mode="after")
    def at_least_one_interval(self) -> "IntervalSchedule":
        if not any([self.every_n_minutes, self.every_n_hours, self.every_n_days]):
            raise ValueError(
                "At least one of every_n_minutes, every_n_hours, or every_n_days is required."
            )
        return self


class OnceSchedule(BaseModel):
    trigger_type: Literal["date"]
    run_at: datetime = Field(..., description="Exact datetime to run the workflow (UTC)")


ScheduleRequest = Union[CronSchedule, IntervalSchedule, OnceSchedule]


# ─────────────────────────────────────────────────────────────────────────────
# RESPONSES
# ─────────────────────────────────────────────────────────────────────────────

class ScheduledWorkflow(BaseModel):
    workflow_id: uuid.UUID
    workflow_name: str
    status: str
    trigger_type: str              # cron | interval | date
    cron_expression: Optional[str]
    timezone: str
    next_run_time: Optional[datetime]
    job_id: str

    model_config = {"from_attributes": True}


class ScheduleResponse(BaseModel):
    workflow_id: uuid.UUID
    job_id: str
    trigger_type: str
    next_run_time: Optional[datetime]
    message: str


class ScheduledListResponse(BaseModel):
    total: int
    jobs: List[ScheduledWorkflow]
