# Smoke test for Master + MasterDispatcher + mailbox integration
# Run with: pytest tests/test_master_integration_smoke.py -v -m integration

import os
import json
import time
import pytest
import threading
from datetime import datetime, timezone

from swarm.master import Master
from swarm.master_dispatcher import get_mailbox_path, get_instructions_dir
from swarm.status_broadcaster import get_ai_swarm_dir


@pytest.mark.integration
def test_master_uses_master_dispatcher():
    """Test: Master.__init__ creates MasterDispatcher instance"""
    master = Master(poll_interval=1.0, cluster_id='test-cluster')

    # Verify dispatcher is MasterDispatcher (not old TaskDispatcher)
    from swarm.master_dispatcher import MasterDispatcher
    assert isinstance(master.dispatcher, MasterDispatcher)
    assert master.dispatcher.cluster_id == 'test-cluster'


@pytest.mark.integration
def test_master_dispatcher_writes_mailbox_on_assign(tmp_path):
    """Test: dispatch_one writes to mailbox after lock acquisition"""
    # Setup test environment
    ai_swarm_dir = str(tmp_path / "ai_swarm")
    os.environ['AI_SWARM_DIR'] = ai_swarm_dir

    from swarm.master_dispatcher import MasterDispatcher, TaskInfo
    from swarm import master_scanner

    dispatcher = MasterDispatcher(cluster_id='test-cluster')

    # Create a test task
    task = TaskInfo(
        task_id='task-smoke-001',
        command='echo smoke test',
        priority=1,
        status='pending'
    )

    # Create tasks.json
    tasks_file = os.path.join(ai_swarm_dir, 'tasks.json')
    with open(tasks_file, 'w') as f:
        json.dump({'tasks': [{
            'id': 'task-smoke-001',
            'prompt': 'echo smoke test',
            'priority': 1,
            'status': 'pending'
        }]}, f)

    # Dispatch to worker-1
    result = dispatcher.dispatch_one(task, 'worker-1')

    assert result is True, "Dispatch should succeed"

    # Verify mailbox was created and written
    mailbox_path = get_mailbox_path('worker-1')
    assert os.path.exists(mailbox_path), "Mailbox file should exist"

    with open(mailbox_path, 'r') as f:
        lines = f.readlines()

    assert len(lines) == 1, "Mailbox should have 1 instruction"

    instruction = json.loads(lines[0])
    assert instruction['task_id'] == 'task-smoke-001'
    assert instruction['action'] == 'RUN_TASK'
    assert 'payload' in instruction

    # Verify tasks.json was updated
    with open(tasks_file, 'r') as f:
        tasks_data = json.load(f)

    task_data = tasks_data['tasks'][0]
    assert task_data['status'] == 'ASSIGNED'
    assert task_data['assigned_worker_id'] == 'worker-1'
    assert 'assigned_at' in task_data


@pytest.mark.integration
def test_mailbox_isolation_between_workers(tmp_path):
    """Test: worker-2 mailbox does not receive task dispatched to worker-1"""
    ai_swarm_dir = str(tmp_path / "ai_swarm")
    os.environ['AI_SWARM_DIR'] = ai_swarm_dir

    from swarm.master_dispatcher import MasterDispatcher, TaskInfo

    dispatcher = MasterDispatcher(cluster_id='test-cluster')

    # Create tasks.json
    tasks_file = os.path.join(ai_swarm_dir, 'tasks.json')
    with open(tasks_file, 'w') as f:
        json.dump({'tasks': [{
            'id': 'task-isolation-001',
            'prompt': 'echo isolation test',
            'priority': 1,
            'status': 'pending'
        }]}, f)

    # Dispatch to worker-1 only
    task = TaskInfo(
        task_id='task-isolation-001',
        command='echo isolation test',
        priority=1,
        status='pending'
    )

    dispatcher.dispatch_one(task, 'worker-1')

    # Verify worker-1 mailbox has the instruction
    mailbox1 = get_mailbox_path('worker-1')
    assert os.path.exists(mailbox1), "worker-1 mailbox should exist"

    with open(mailbox1, 'r') as f:
        instructions1 = f.readlines()

    assert len(instructions1) == 1, "worker-1 should have 1 instruction"

    # Verify worker-2 mailbox does NOT exist (or is empty)
    mailbox2 = get_mailbox_path('worker-2')
    if os.path.exists(mailbox2):
        with open(mailbox2, 'r') as f:
            instructions2 = f.readlines()
        assert len(instructions2) == 0, "worker-2 mailbox should be empty"
    else:
        # Mailbox doesn't exist, also acceptable
        assert True


@pytest.mark.integration
def test_master_loop_with_mock_workers(tmp_path):
    """Test: Master run loop with simulated worker statuses"""
    ai_swarm_dir = str(tmp_path / "ai_swarm")
    os.makedirs(ai_swarm_dir, exist_ok=True)
    os.environ['AI_SWARM_DIR'] = ai_swarm_dir

    # Create tasks.json with a pending task
    tasks_file = os.path.join(ai_swarm_dir, 'tasks.json')
    with open(tasks_file, 'w') as f:
        json.dump({'tasks': [{
            'id': 'task-loop-001',
            'prompt': 'echo loop test',
            'priority': 1,
            'status': 'pending'
        }]}, f)

    # Create status.log with idle worker
    status_log = os.path.join(ai_swarm_dir, 'status.log')
    with open(status_log, 'w') as f:
        # Worker-1 is idle (DONE state, no lock)
        f.write(json.dumps({
            'ts': datetime.now(timezone.utc).isoformat(),
            'worker_id': 'worker-1',
            'task_id': '',
            'state': 'DONE',
            'message': 'Idle and ready'
        }) + '\n')

    # Start master (will run one iteration then we stop it)
    master = Master(poll_interval=0.1, cluster_id='test-loop')

    # Run for a short time
    stop_event = threading.Event()

    def run_master():
        master.run()

    master_thread = threading.Thread(target=run_master, daemon=True)
    master_thread.start()

    # Wait for dispatch to happen
    time.sleep(0.5)

    # Stop master
    master.running = False
    master_thread.join(timeout=1.0)

    # Verify mailbox was written
    mailbox1 = get_mailbox_path('worker-1')
    assert os.path.exists(mailbox1), "worker-1 mailbox should exist after dispatch"

    with open(mailbox1, 'r') as f:
        instructions = f.readlines()

    assert len(instructions) >= 1, f"Expected at least 1 instruction, got {len(instructions)}"

    # Verify the instruction format
    first_instruction = json.loads(instructions[0])
    assert first_instruction['action'] == 'RUN_TASK'
    assert 'task_id' in first_instruction
    assert 'payload' in first_instruction
