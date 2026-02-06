#!/usr/bin/env python3
"""
Master Dispatcher Module for AI Swarm System

Provides FIFO task dispatch to idle workers with atomic lock acquisition.
Coordinates task allocation from queue to available workers.
"""

import asyncio
import json
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, List, Dict

from swarm import master_scanner
from swarm import task_lock
from swarm import status_broadcaster


# ==================== Constants ====================

DEFAULT_TASKS_FILE = 'tasks.json'
ENV_TASKS_FILE = 'AI_SWARM_TASKS_FILE'
DEFAULT_AI_SWARM_DIR = '/tmp/ai_swarm'
ENV_POLL_INTERVAL = 'AI_SWARM_POLL_INTERVAL'
DEFAULT_POLL_INTERVAL = 1.0
DEFAULT_INSTRUCTIONS_DIR = 'instructions'


# ==================== Helper Functions ====================

def get_ai_swarm_dir() -> str:
    """
    Get AI_SWARM_DIR from environment variable or use default.

    Returns:
        str: Path to AI Swarm directory
    """
    return os.environ.get('AI_SWARM_DIR', DEFAULT_AI_SWARM_DIR)


def get_instructions_dir() -> str:
    """
    Get instructions directory path.

    Returns:
        str: Path to instructions directory
    """
    return os.path.join(get_ai_swarm_dir(), DEFAULT_INSTRUCTIONS_DIR)


def get_mailbox_path(worker_id: str) -> str:
    """
    Get mailbox file path for a worker.

    Args:
        worker_id: Worker identifier

    Returns:
        str: Path to worker's mailbox JSONL file
    """
    return os.path.join(get_instructions_dir(), f'{worker_id}.jsonl')


def get_tasks_file_path() -> str:
    """
    Get tasks.json file path from environment or default.

    Returns:
        str: Path to tasks.json file
    """
    base_dir = get_ai_swarm_dir()
    filename = os.environ.get(ENV_TASKS_FILE, DEFAULT_TASKS_FILE)
    return os.path.join(base_dir, filename)


def get_poll_interval() -> float:
    """
    Get poll interval from environment variable or use default.

    Returns:
        float: Poll interval in seconds (default 1.0)
    """
    interval_str = os.environ.get(ENV_POLL_INTERVAL)
    if interval_str:
        try:
            return float(interval_str)
        except ValueError:
            pass
    return DEFAULT_POLL_INTERVAL


# ==================== Dataclasses ====================

@dataclass
class TaskInfo:
    """
    Represents a task from the task queue.

    Attributes:
        task_id: Unique task identifier
        command: Command to execute (e.g., prompt for agent)
        priority: Task priority (1=highest, 5=lowest)
        status: Task status (pending, assigned, done, skipped)
    """
    task_id: str
    command: str
    priority: int
    status: str


@dataclass
class DispatchResult:
    """
    Result of a dispatch operation.

    Attributes:
        success: True if dispatch succeeded
        task_id: Task ID that was dispatched
        worker_id: Worker ID that received the task
        reason: Failure reason if success is False
    """
    success: bool
    task_id: Optional[str]
    worker_id: Optional[str]
    reason: Optional[str]


# ==================== MasterDispatcher Class ====================

class MasterDispatcher:
    """
    Master Dispatcher for FIFO task allocation to idle workers.

    Dispatch algorithm:
    1. Read tasks.json queue from head
    2. Find first task without valid lock
    3. Try to acquire lock (O_CREAT|O_EXCL)
    4. If acquired -> dispatch, update status to ASSIGNED
    5. If not acquired -> skip to next task

    Idle worker definition:
    - Status is DONE/SKIP/ERROR AND holds no active lock
    - OR has heartbeat but no active task

    Usage:
        dispatcher = MasterDispatcher('cluster-1')
        dispatcher.dispatch_loop(stop_event)
    """

    def __init__(self, cluster_id: str):
        """
        Initialize MasterDispatcher.

        Args:
            cluster_id: Unique identifier for the swarm cluster
        """
        self.cluster_id = cluster_id
        self._ai_swarm_dir = get_ai_swarm_dir()
        self._instructions_dir = get_instructions_dir()
        self._scanner = master_scanner.MasterScanner(cluster_id)
        self._lock_manager = task_lock.TaskLockManager(worker_id='master-dispatcher')
        self._broadcaster = status_broadcaster.StatusBroadcaster(
            worker_id='master-dispatcher'
        )

        # Ensure instructions directory exists
        os.makedirs(self._instructions_dir, exist_ok=True)

    def _get_tasks_file_path(self) -> str:
        """
        Get the path to tasks.json file.

        Returns:
            str: Path to tasks.json
        """
        return get_tasks_file_path()

    def load_tasks(self) -> List[TaskInfo]:
        """
        Load tasks from tasks.json file.

        Returns:
            List[TaskInfo]: List of tasks from queue
        """
        tasks_file = self._get_tasks_file_path()

        if not os.path.exists(tasks_file):
            return []

        try:
            with open(tasks_file, 'r') as f:
                data = json.load(f)
                tasks_list = data.get('tasks', [])

            tasks = []
            for task_dict in tasks_list:
                # Map task queue format to TaskInfo
                task = TaskInfo(
                    task_id=task_dict.get('id', ''),
                    command=task_dict.get('prompt', ''),
                    priority=task_dict.get('priority', 999),
                    status=task_dict.get('status', 'pending')
                )
                tasks.append(task)

            return tasks

        except (json.JSONDecodeError, FileNotFoundError, IOError):
            return []

    def is_worker_idle(self, worker_status: master_scanner.WorkerStatus) -> bool:
        """
        Check if a worker is idle and ready for new tasks.

        Idle worker criteria:
        - Status is DONE/SKIP/ERROR AND holds no active lock
        - OR Status is START AND has no task_id (just started, waiting for first task)

        Args:
            worker_status: Worker status from scanner

        Returns:
            bool: True if worker is idle, False otherwise
        """
        # Workers with no status are not idle (they're unknown)
        if worker_status.state is None:
            return False

        # Workers in WAIT state are busy (waiting for human input)
        if worker_status.state == 'WAIT':
            return False

        # Workers in START state with no task_id are idle (just started, waiting for first task)
        # Conservative: if task_id exists (even empty string), worker is busy processing
        # Use 'not task_id' to catch both None and empty string
        if worker_status.state == 'START' and not worker_status.task_id:
            return True

        # Workers with DONE, SKIP, or ERROR state are idle
        # DONE/SKIP/ERROR: worker completed previous task
        if worker_status.state in ('DONE', 'SKIP', 'ERROR'):
            # Check if worker holds any active lock
            # If worker has a task_id, check if it's locked
            if worker_status.task_id:
                lock_info = self._scanner.read_lock_state(worker_status.task_id)
                # If lock exists and is valid, worker is still busy
                if lock_info and not lock_info.is_expired():
                    return False

            # No active lock, worker is idle
            return True

        # All other states are not idle
        return False

    def find_idle_worker(
        self,
        worker_statuses: Dict[str, master_scanner.WorkerStatus]
    ) -> Optional[str]:
        """
        Find an idle worker from the worker statuses.

        Args:
            worker_statuses: Dict mapping worker_id to WorkerStatus

        Returns:
            str: Worker ID if idle worker found, None otherwise
        """
        for worker_id, status in worker_statuses.items():
            if self.is_worker_idle(status):
                return worker_id
        return None

    def dispatch_one(self, task: TaskInfo, worker_id: str) -> bool:
        """
        Dispatch a single task to a worker.

        Dispatch sequence:
        1. Re-check tasks.json to verify task is still pending (prevent stale data)
        2. Acquire task lock using worker's ID (skip if already locked)
        3. Broadcast ASSIGNED status with meta
        4. Write RUN_TASK instruction to worker's mailbox (JSONL)
        5. Update tasks.json status to ASSIGNED
        6. Verify status update succeeded, rollback on failure

        Args:
            task: Task to dispatch
            worker_id: Worker to dispatch to

        Returns:
            bool: True if dispatch succeeded, False otherwise
        """
        # === 1. 派发前: 重新检查 tasks.json ===
        current_tasks = self.load_tasks()
        current_task = next((t for t in current_tasks if t.task_id == task.task_id), None)
        if current_task and current_task.status != 'pending':
            # 任务已被分配，跳过
            return False

        # 2. Acquire task lock using worker's ID (not master's)
        # Create temporary lock manager for the target worker
        worker_lock_manager = task_lock.TaskLockManager(worker_id=worker_id)
        acquired = worker_lock_manager.acquire_lock(task.task_id)

        if not acquired:
            # Task is already locked, skip
            return False

        try:
            # === 3. Broadcast ASSIGNED status with meta ===
            import time
            ts_ms = int(time.time() * 1000)
            self._broadcaster._broadcast(
                state=status_broadcaster.BroadcastState.ASSIGNED,
                task_id=task.task_id,
                message=f'Task assigned to {worker_id}',
                meta={
                    'assigned_worker_id': worker_id
                }
            )

            # === 4. Write to mailbox (JSONL append-only) ===
            self._write_to_mailbox(task, worker_id)

            # === 5. Update tasks.json ===
            update_success = self._update_task_status(task.task_id, worker_id, ts_ms)

            if not update_success:
                # 状态更新失败，回滚
                self._rollback_dispatch(task.task_id, worker_id)
                return False

            # === 6. 派发后: 再次验证状态 ===
            updated_tasks = self.load_tasks()
            updated_task = next((t for t in updated_tasks if t.task_id == task.task_id), None)
            if not updated_task or updated_task.status != 'ASSIGNED':
                # 验证失败，回滚
                self._rollback_dispatch(task.task_id, worker_id)
                return False

            return True

        except Exception as e:
            # If dispatch fails, release the lock
            print(f"[MasterDispatcher] Dispatch failed for {task.task_id}: {e}")
            self._rollback_dispatch(task.task_id, worker_id)
            return False

    def _rollback_dispatch(self, task_id: str, worker_id: str) -> None:
        """
        Rollback dispatch operation: release lock.

        Args:
            task_id: Task ID
            worker_id: Worker ID
        """
        try:
            worker_lock_manager = task_lock.TaskLockManager(worker_id=worker_id)
            worker_lock_manager.release_lock(task_id)
        except Exception:
            pass

    def _write_to_mailbox(self, task: TaskInfo, worker_id: str) -> None:
        """
        Write RUN_TASK instruction to worker's mailbox.

        Args:
            task: Task to dispatch
            worker_id: Worker to dispatch to
        """
        import time
        mailbox_path = get_mailbox_path(worker_id)

        # Ensure instructions directory exists
        os.makedirs(os.path.dirname(mailbox_path), exist_ok=True)

        # Build instruction
        ts_ms = int(time.time() * 1000)
        instruction = {
            'ts': ts_ms,
            'task_id': task.task_id,
            'action': 'RUN_TASK',
            'payload': {
                'id': task.task_id,
                'prompt': task.command,
                'priority': task.priority
            },
            'attempt': 1
        }

        # Append to mailbox (JSONL)
        with open(mailbox_path, 'a') as f:
            f.write(json.dumps(instruction) + '\n')

    def _update_task_status(self, task_id: str, worker_id: str, ts_ms: int) -> bool:
        """
        Update task status in tasks.json to ASSIGNED.

        Uses atomic write (temp file + rename) to ensure consistency.

        Args:
            task_id: Task ID
            worker_id: Worker ID
            ts_ms: Timestamp in milliseconds

        Returns:
            bool: True if update succeeded, False otherwise
        """
        tasks_file = self._get_tasks_file_path()

        if not os.path.exists(tasks_file):
            return False

        # Use temp file with PID suffix to avoid conflicts
        temp_path = tasks_file + '.tmp.' + str(os.getpid())

        try:
            with open(tasks_file, 'r') as f:
                data = json.load(f)

            # Find and update the task
            found = False
            for task_dict in data.get('tasks', []):
                if task_dict.get('id') == task_id:
                    task_dict['status'] = 'ASSIGNED'
                    task_dict['assigned_worker_id'] = worker_id
                    task_dict['assigned_at'] = ts_ms
                    found = True
                    break

            if not found:
                return False

            # Atomic write: write to temp file first, then rename
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=2)
            os.replace(temp_path, tasks_file)

            return True

        except (json.JSONDecodeError, FileNotFoundError, IOError, OSError) as e:
            print(f"[MasterDispatcher] Failed to update tasks.json: {e}")
            # Clean up temp file if exists
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            return False

    def dispatch_all(
        self,
        worker_statuses: Dict[str, master_scanner.WorkerStatus]
    ) -> List[DispatchResult]:
        """
        Dispatch tasks to all idle workers.

        Args:
            worker_statuses: Dict mapping worker_id to WorkerStatus

        Returns:
            List[DispatchResult]: Results of dispatch attempts
        """
        results = []

        # Load pending tasks
        all_tasks = self.load_tasks()

        # Filter pending tasks and sort by priority (FIFO within same priority)
        pending_tasks = [
            task for task in all_tasks
            if task.status == 'pending'
        ]
        pending_tasks.sort(key=lambda t: t.priority)

        if not pending_tasks:
            return results

        # Find idle workers
        idle_workers = [
            worker_id for worker_id, status in worker_statuses.items()
            if self.is_worker_idle(status)
        ]

        if not idle_workers:
            return results

        # Dispatch one task per idle worker
        for worker_id in idle_workers:
            if not pending_tasks:
                break

            # Find first task that can be locked
            for i, task in enumerate(pending_tasks):
                if self.dispatch_one(task, worker_id):
                    results.append(DispatchResult(
                        success=True,
                        task_id=task.task_id,
                        worker_id=worker_id,
                        reason=None
                    ))
                    # Remove dispatched task from list
                    pending_tasks.pop(i)
                    break
                else:
                    # Couldn't acquire lock, try next task
                    continue

        return results

    def dispatch_loop(self, stop_event: threading.Event) -> None:
        """
        Main dispatch loop that runs continuously.

        Scans for idle workers and dispatches pending tasks.

        Args:
            stop_event: Event to signal graceful shutdown
        """
        while not stop_event.is_set():
            # Get worker statuses from scanner
            worker_statuses = self._scanner.scan_all()

            # Dispatch to idle workers
            results = self.dispatch_all(worker_statuses)

            # Log results (could be enhanced with proper logging)
            if results:
                for result in results:
                    if result.success:
                        pass  # Successful dispatch logged via broadcast

            # Sleep between iterations
            interval = get_poll_interval()
            stop_event.wait(interval)


# ==================== Factory Function ====================

def create_dispatcher(cluster_id: str) -> MasterDispatcher:
    """
    Factory function to create a MasterDispatcher instance.

    Args:
        cluster_id: Unique identifier for the swarm cluster

    Returns:
        MasterDispatcher: Configured dispatcher instance
    """
    return MasterDispatcher(cluster_id)
