"""
AutoFlow AI X — Celery Application
====================================
Central Celery instance.  Import this object everywhere.

Start worker:
  celery -A backend.workers.celery_app worker --loglevel=info -Q default,high_priority,scheduled

Start Beat (for scheduled workflows):
  celery -A backend.workers.celery_app beat --loglevel=info

Start Flower:
  celery -A backend.workers.celery_app flower --port=5555
"""

import os
from celery import Celery

_REDIS_URL      = os.environ.get("REDIS_URL",             "redis://localhost:6379/0")
_BROKER_URL     = os.environ.get("CELERY_BROKER_URL",     _REDIS_URL)
_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", _REDIS_URL)

celery_app = Celery(
    "autoflow",
    broker=_BROKER_URL,
    backend=_RESULT_BACKEND,
    include=["backend.workers.tasks"],
)

celery_app.conf.update(
    task_serializer            = "json",
    result_serializer          = "json",
    accept_content             = ["json"],
    result_expires             = 60 * 60 * 24 * 7,
    task_default_queue         = "default",
    task_queues                = {
        "default":       {"exchange": "default",       "routing_key": "default"},
        "high_priority": {"exchange": "high_priority", "routing_key": "high_priority"},
        "scheduled":     {"exchange": "scheduled",     "routing_key": "scheduled"},
    },
    task_acks_late             = True,
    task_reject_on_worker_lost = True,
    worker_prefetch_multiplier = 1,
    task_track_started         = True,
    task_max_retries           = 3,
    task_default_retry_delay   = 30,
    enable_utc                 = True,
    timezone                   = "UTC",
    beat_scheduler             = "redbeat.RedBeatScheduler",
    redbeat_redis_url          = _BROKER_URL,
    redbeat_key_prefix         = "autoflow:beat:",
)
