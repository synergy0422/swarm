#!/usr/bin/env python3
"""
Master Scanner Module for AI Swarm System

Provides periodic scanning of worker status and task locks for Master coordination.
Reads from status.log (JSONL) and locks/ directory to enable task dispatch.
"""

import os
import json
import time
import threading
from dataclasses import dataclass
from typing import Optional, List, Dict

from swarm import task_lock


# Default configuration
DEFAULT_POLL_INTERVAL = 1.0
ENV_POLL_INTERVAL = 'AI_SWARM_POLL_INTERVAL'
DEFAULT_AI_SWARM_DIR = '/tmp/ai_swarm'


def get_ai_swarm_dir() -> str:
    """
    Get AI_SWARM_DIR from environment variable or use default.

    Returns:
        str: Path to AI Swarm directory
    """
    return os.environ.get('AI_SWARM_DIR', DEFAULT_AI_SWARM_DIR)


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


@dataclass
class WorkerStatus:
    """
    Represents the current status of a worker.

    Attributes:
        worker_id: ID of the worker
        state: Current state from status.log (START, DONE, WAIT, ERROR, HELP, SKIP)
        task_id: ID of the current task
        timestamp: ISO 8601 timestamp of the last status update
        message: Optional human-readable message
    """
    worker_id: str
    state: Optional[str]
    task_id: Optional[str]
    timestamp: Optional[str]
    message: Optional[str]


class MasterScanner:
    """
    Master Scanner for periodic worker and task lock scanning.

    Monitors:
    - Worker status from status.log (JSONL format)
    - Task lock state from locks/ directory
    - Tmux pane output for WAIT detection

    Usage:
        scanner = MasterScanner('cluster-1')
        worker_statuses = scanner.read_worker_status()
        lock_info = scanner.read_lock_state('task-123')
    """

    def __init__(self, cluster_id: str):
        """
        Initialize MasterScanner with cluster ID.

        Args:
            cluster_id: Unique identifier for the swarm cluster
        """
        self.cluster_id = cluster_id
        self._ai_swarm_dir = get_ai_swarm_dir()
        self._status_log_path = None
        self._locks_dir = None
        self._ensure_directories()

    def _get_status_log_path(self) -> str:
        """
        Get the full path to the status log file.

        Returns:
            str: Path to status.log
        """
        if self._status_log_path is None:
            self._status_log_path = os.path.join(
                self._ai_swarm_dir,
                'status.log'
            )
        return self._status_log_path

    def _get_locks_dir(self) -> str:
        """
        Get the locks directory path.

        Returns:
            str: Path to locks directory
        """
        if self._locks_dir is None:
            self._locks_dir = os.path.join(
                self._ai_swarm_dir,
                'locks'
            )
        return self._locks_dir

    def _ensure_directories(self) -> None:
        """
        Ensure the AI_SWARM_DIR exists, creating it if necessary.
        """
        os.makedirs(self._ai_swarm_dir, exist_ok=True)

    def read_worker_status(self) -> List[WorkerStatus]:
        """
        Read worker status from status.log (JSONL format).

        Returns the last status entry for each worker based on timestamp.
        If status.log doesn't exist or is empty, returns empty list.

        Returns:
            List[WorkerStatus]: List of worker statuses (last entry per worker)
        """
        status_log_path = self._get_status_log_path()

        if not os.path.exists(status_log_path):
            return []

        worker_entries: Dict[str, dict] = {}

        try:
            with open(status_log_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        entry = json.loads(line)
                        worker_id = entry.get('worker_id')
                        if not worker_id:
                            continue

                        # Keep the last entry for each worker
                        worker_entries[worker_id] = entry

                    except (json.JSONDecodeError, KeyError):
                        # Skip malformed lines
                        continue

        except (IOError, OSError):
            return []

        # Convert to WorkerStatus objects
        statuses = []
        for worker_id, entry in worker_entries.items():
            status = WorkerStatus(
                worker_id=worker_id,
                state=entry.get('state'),
                task_id=entry.get('task_id'),
                timestamp=entry.get('ts'),
                message=entry.get('message', '')
            )
            statuses.append(status)

        return statuses

    def read_lock_state(self, task_id: str) -> Optional[task_lock.LockInfo]:
        """
        Read lock state for a specific task.

        Uses TaskLockManager.get_lock_info() to retrieve lock information.
        Returns None if task is not locked.

        Args:
            task_id: Task ID to check

        Returns:
            LockInfo if locked, None otherwise
        """
        # Create a temporary TaskLockManager instance to check lock state
        # Use a dummy worker_id since we're only reading
        temp_manager = task_lock.TaskLockManager(worker_id='master-scanner')
        return temp_manager.get_lock_info(task_id)

    def get_pane_output(self, agent_id: str) -> str:
        """
        Capture current output from an agent's tmux pane.

        This method delegates to TmuxSwarmManager.capture_agent_output().
        Note: This requires an active TmuxSwarmManager session.

        Args:
            agent_id: ID of the agent to capture output from

        Returns:
            str: Current output from the pane

        Raises:
            AgentNotFoundError: If agent is not found
        """
        # Import here to avoid circular dependency
        from swarm import tmux_manager

        # This is a placeholder - the actual TmuxSwarmManager instance
        # would need to be passed in or managed separately
        # For now, return empty string
        return ''

    def scan_all(self) -> Dict[str, WorkerStatus]:
        """
        Scan all workers and return their current status.

        This is the main scan operation called each iteration of scan_loop().

        Returns:
            Dict mapping worker_id to WorkerStatus
        """
        worker_statuses = self.read_worker_status()
        return {status.worker_id: status for status in worker_statuses}

    def scan_loop(self, stop_event: threading.Event) -> None:
        """
        Main scanning loop for continuous monitoring.

        Runs until stop_event is set, scanning workers and locks
        at the configured poll interval.

        Args:
            stop_event: Threading event to signal graceful shutdown
        """
        while not stop_event.is_set():
            # Scan all workers
            self.scan_all()

            # Sleep for poll interval
            interval = get_poll_interval()
            stop_event.wait(interval)


def create_scanner(cluster_id: str) -> MasterScanner:
    """
    Factory function to create a MasterScanner instance.

    Args:
        cluster_id: Unique identifier for the swarm cluster

    Returns:
        MasterScanner: Configured scanner instance
    """
    return MasterScanner(cluster_id)
