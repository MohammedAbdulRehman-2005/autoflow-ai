import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.database.models import ExecutionEvent, RunStatus

class EventRepository:
    """Repository for appending and fetching execution events."""

    def __init__(self, db: Session):
        self.db = db

    def append(self, run_id: uuid.UUID, event_type: str, node_id: Optional[uuid.UUID] = None, payload: Optional[Dict[str, Any]] = None) -> ExecutionEvent:
        """Appends a new event to the ledger."""
        event = ExecutionEvent(
            run_id=run_id,
            node_id=node_id,
            event_type=event_type,
            payload=payload or {}
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def get_events(self, run_id: uuid.UUID) -> List[ExecutionEvent]:
        """Fetches all events for a given run, ordered by creation time."""
        return self.db.query(ExecutionEvent).filter(ExecutionEvent.run_id == run_id).order_by(ExecutionEvent.id.asc()).all()


class StateHydrator:
    """Hydrates exact workflow execution state from an event ledger."""

    @staticmethod
    def compute_run_status(events: List[ExecutionEvent]) -> RunStatus:
        """
        Reconstructs the WorkflowRun status from the event log.
        A very naive implementation for Phase 1.
        """
        if not events:
            return RunStatus.pending

        current_status = RunStatus.pending

        for event in events:
            if event.event_type == "RUN_STARTED" or event.event_type == "RUN_RUNNING":
                current_status = RunStatus.running
            elif event.event_type == "RUN_FAILED":
                current_status = RunStatus.failed
            elif event.event_type == "RUN_SUCCESS":
                current_status = RunStatus.success
            elif event.event_type == "RUN_CANCELLED":
                current_status = RunStatus.cancelled
            elif event.event_type == "RUN_RETRYING":
                current_status = RunStatus.retrying
            elif event.event_type == "RUN_SUSPENDED":
                # Assuming we might add this state in the future,
                # but models.py only defines: pending, running, success, failed, cancelled, retrying
                pass

        return current_status

    @staticmethod
    def compute_node_statuses(events: List[ExecutionEvent]) -> Dict[uuid.UUID, RunStatus]:
        """
        Reconstructs the status of individual nodes from the event log.
        Returns a map of node_id -> RunStatus
        """
        node_statuses: Dict[uuid.UUID, RunStatus] = {}

        for event in events:
            if not event.node_id:
                continue

            if event.event_type == "NODE_STARTED" or event.event_type == "NODE_RUNNING":
                node_statuses[event.node_id] = RunStatus.running
            elif event.event_type == "NODE_SUCCESS":
                node_statuses[event.node_id] = RunStatus.success
            elif event.event_type == "NODE_FAILED":
                node_statuses[event.node_id] = RunStatus.failed
            elif event.event_type == "NODE_CANCELLED":
                node_statuses[event.node_id] = RunStatus.cancelled

        return node_statuses
