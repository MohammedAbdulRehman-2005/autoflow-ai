import uuid
import pytest
from backend.database.models import ExecutionEvent, RunStatus
from backend.workflow.engine.event_store import StateHydrator

def test_state_hydrator_compute_run_status():
    run_id = uuid.uuid4()
    events = [
        ExecutionEvent(run_id=run_id, event_type="RUN_STARTED", payload={}),
        ExecutionEvent(run_id=run_id, event_type="RUN_RETRYING", payload={}),
        ExecutionEvent(run_id=run_id, event_type="RUN_SUCCESS", payload={})
    ]

    status = StateHydrator.compute_run_status(events)
    assert status == RunStatus.success

def test_state_hydrator_compute_node_statuses():
    run_id = uuid.uuid4()
    node1_id = uuid.uuid4()
    node2_id = uuid.uuid4()

    events = [
        ExecutionEvent(run_id=run_id, node_id=node1_id, event_type="NODE_STARTED", payload={}),
        ExecutionEvent(run_id=run_id, node_id=node1_id, event_type="NODE_SUCCESS", payload={}),
        ExecutionEvent(run_id=run_id, node_id=node2_id, event_type="NODE_STARTED", payload={}),
        ExecutionEvent(run_id=run_id, node_id=node2_id, event_type="NODE_FAILED", payload={})
    ]

    statuses = StateHydrator.compute_node_statuses(events)
    assert statuses[node1_id] == RunStatus.success
    assert statuses[node2_id] == RunStatus.failed
