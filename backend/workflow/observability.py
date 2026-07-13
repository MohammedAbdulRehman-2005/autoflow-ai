"""
AutoFlow AI X — Observability & Instrumentation  (Sprint 3.5, Goal 14)
=======================================================================
Lightweight, zero-dependency timing instrumentation.

Design principles:
  - No external APM dependencies (Prometheus, DataDog, etc.).
  - All measurements are opt-in context managers or decorators.
  - Timings are logged at DEBUG level and optionally stored in the
    current request/execution context for downstream consumers
    (e.g. the metrics endpoint or AI cost estimation).
  - This module is ADDITIVE ONLY — callers that ignore it see zero
    behavioural change.

Instrumented stages (Sprint 3.5):
  planner_time       — total time in editor_engine.add_step()
  capability_match_time  — time in CapabilityRegistry.match()
  validation_time    — time in ValidationPipeline.run()
  mutation_time      — time in mutationService equivalent (backend)
  execution_time     — time in WorkflowRunner.execute_single_node()

Future stages (not implemented yet):
  embedding_time, llm_select_time, delta_apply_time, db_write_time

Usage:
    from backend.workflow.observability import timer, Span

    # As a context manager:
    with timer('capability_match_time') as span:
        result = CapabilityRegistry.match(intent)
    print(span.duration_ms)  # e.g. 1.23

    # As part of a SpanCollection:
    spans = SpanCollection()
    with spans.measure('planner_time'):
        ...
    print(spans.to_dict())  # {'planner_time': 42.1, ...}
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, Generator, Optional

logger = logging.getLogger(__name__)

# ─── Known span names (not enforced — just for IDE discoverability) ────────────
SPAN_PLANNER            = 'planner_time'
SPAN_CAPABILITY_MATCH   = 'capability_match_time'
SPAN_VALIDATION         = 'validation_time'
SPAN_MUTATION           = 'mutation_time'
SPAN_EXECUTION          = 'execution_time'
SPAN_LLM_SELECT         = 'llm_select_time'        # future
SPAN_DELTA_APPLY        = 'delta_apply_time'        # future
SPAN_DB_WRITE           = 'db_write_time'           # future


@dataclass
class Span:
    """
    A single named timing measurement.

    Attributes
    ----------
    name        : Logical stage name (e.g. 'capability_match_time')
    start_ns    : Monotonic clock at start (nanoseconds)
    end_ns      : Monotonic clock at end (nanoseconds) — 0 until span closes
    error       : Exception message if the span exited abnormally
    """
    name: str
    start_ns: int = field(default_factory=lambda: time.monotonic_ns())
    end_ns: int = 0
    error: Optional[str] = None

    def close(self, error: Optional[str] = None) -> None:
        """Finalise the span. Idempotent."""
        if self.end_ns == 0:
            self.end_ns = time.monotonic_ns()
        if error:
            self.error = error

    @property
    def duration_ms(self) -> float:
        """Wall-clock duration in milliseconds. 0.0 if span not yet closed."""
        if self.end_ns == 0:
            return 0.0
        return (self.end_ns - self.start_ns) / 1_000_000

    @property
    def is_closed(self) -> bool:
        return self.end_ns != 0

    def to_dict(self) -> Dict[str, object]:
        return {
            'name': self.name,
            'duration_ms': round(self.duration_ms, 3),
            'error': self.error,
        }


class SpanCollection:
    """
    A bag of named spans for a single request/operation lifecycle.

    Typical use: create one per request in editor_engine.add_step(),
    populate it with measure() calls, and attach it to the response
    for downstream logging or metrics export.
    """

    def __init__(self) -> None:
        self._spans: Dict[str, Span] = {}

    @contextmanager
    def measure(self, name: str) -> Generator[Span, None, None]:
        """Context manager that creates, runs, and closes a Span."""
        span = Span(name=name)
        self._spans[name] = span
        try:
            yield span
        except Exception as exc:
            span.close(error=str(exc))
            logger.debug('[Observability] %s FAILED in %.2fms: %s', name, span.duration_ms, exc)
            raise
        else:
            span.close()
            logger.debug('[Observability] %s completed in %.2fms', name, span.duration_ms)

    def get(self, name: str) -> Optional[Span]:
        """Return a span by name, or None."""
        return self._spans.get(name)

    def duration_ms(self, name: str) -> Optional[float]:
        """Return duration in ms for a named span, or None if not measured."""
        span = self._spans.get(name)
        return round(span.duration_ms, 3) if span and span.is_closed else None

    def to_dict(self) -> Dict[str, Optional[float]]:
        """Serialise all closed span durations (ms) as a flat dict."""
        return {
            name: round(span.duration_ms, 3)
            for name, span in self._spans.items()
            if span.is_closed
        }

    def log_summary(self, logger_: Optional[logging.Logger] = None, level: int = logging.DEBUG) -> None:
        """Emit one log line per span. Useful at the end of a request."""
        _log = logger_ or logger
        for name, span in self._spans.items():
            if span.is_closed:
                _log.log(level, '[Observability] %-30s %.3fms', name, span.duration_ms)


@contextmanager
def timer(name: str) -> Generator[Span, None, None]:
    """
    Standalone context manager for ad-hoc span measurement.

    Example::

        with timer('capability_match_time') as span:
            result = CapabilityRegistry.match(intent)
        logger.info('match took %.2fms', span.duration_ms)
    """
    span = Span(name=name)
    try:
        yield span
    except Exception as exc:
        span.close(error=str(exc))
        logger.debug('[Observability] %s FAILED: %s', name, exc)
        raise
    else:
        span.close()
        logger.debug('[Observability] %s: %.3fms', name, span.duration_ms)
