"""
AutoFlow AI X — Event Bus  (RFC-001 §6)
=========================================
Minimal synchronous, in-process event bus for Sprint 1.

Design choices:
  - Class-level subscriber registry (module singleton pattern).
  - Synchronous dispatch — no async/await. Fast enough for in-process use.
  - Swallowable handler errors (logged, never crash the emitter).
  - Sprint 2+ can replace this with an async or distributed bus without
    changing the emit/subscribe API.

Standard events emitted in Sprint 1:
  - "ExecutionStarted"   { run_id, workflow_id, triggered_by }
  - "ExecutionFinished"  { run_id, workflow_id, status }
  - "NodeFailed"         { run_id, node_id, error }

# TODO: RFC-001 §4, Sprint 3 — Capability Registry will also emit events here.
"""

import logging
from collections import defaultdict
from typing import Callable

logger = logging.getLogger(__name__)


class EventBus:
    """
    Module-level event bus.

    Usage:
        # Subscribe
        event_bus.subscribe("NodeFailed", my_handler)

        # Emit (e.g. from WorkflowRunner)
        event_bus.emit("NodeFailed", {"run_id": "...", "node_id": "...", "error": "..."})
    """

    def __init__(self) -> None:
        self._listeners: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Register a handler for the given event type."""
        self._listeners[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """Remove a specific handler. No-op if not registered."""
        try:
            self._listeners[event_type].remove(handler)
        except ValueError:
            pass

    def emit(self, event_type: str, payload: dict) -> None:
        """
        Dispatch an event to all registered handlers.

        Handler exceptions are caught and logged — a failing handler never
        interrupts the emitter or other handlers.
        """
        handlers = self._listeners.get(event_type, [])
        for handler in handlers:
            try:
                handler(payload)
            except Exception as exc:
                logger.error(
                    "[EventBus] Handler '%s' raised for event '%s': %s",
                    getattr(handler, "__name__", repr(handler)),
                    event_type,
                    exc,
                    exc_info=True,
                )

    def clear(self) -> None:
        """Remove all subscribers. Primarily for test isolation."""
        self._listeners.clear()


# Module-level singleton — import this everywhere.
event_bus = EventBus()
