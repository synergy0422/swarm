#!/usr/bin/env python3
"""
Status Broadcaster Module for AI Swarm System

Provides JSONL-based status logging for multi-agent coordination.
Broadcasts task state changes (START, DONE, WAIT, ERROR, HELP, SKIP)
to a shared status log file for Master coordination.
"""

import os
import json
import fcntl
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


# Default configuration
DEFAULT_STATUS_LOG = 'status.log'
DEFAULT_AI_SWARM_DIR = '/tmp/ai_swarm'


class BroadcastState(str, Enum):
    """
    Task state enumeration for status broadcasting.

    States are fixed and not细分 - use meta field for additional context.
    """
    START = 'START'
    DONE = 'DONE'
    WAIT = 'WAIT'
    ERROR = 'ERROR'
    HELP = 'HELP'
    SKIP = 'SKIP'


def get_ai_swarm_dir() -> str:
    """
    Get AI_SWARM_DIR from environment variable or use default.

    Returns:
        str: Path to AI Swarm directory
    """
    return os.environ.get('AI_SWARM_DIR', DEFAULT_AI_SWARM_DIR)


class StatusBroadcaster:
    """
    Manages status broadcasting to a shared JSONL log file.

    Used by Workers to report task state changes to Master.
    Log format: One JSON object per line (JSON Lines format).

    Example:
        {"state": "START", "task_id": "task-123", "timestamp": "2026-01-31T12:00:00.000Z", "message": "开始执行"}
        {"state": "DONE", "task_id": "task-123", "timestamp": "2026-01-31T12:00:05.000Z", "message": "执行完成"}
    """

    def __init__(self, worker_id: str):
        """
        Initialize StatusBroadcaster with worker ID.

        Args:
            worker_id: Unique identifier for this worker
        """
        self.worker_id = worker_id
        self._ai_swarm_dir = get_ai_swarm_dir()
        self._status_log_path = None
        self._ensure_directory()

    def _get_status_log_path(self) -> str:
        """
        Get the full path to the status log file.

        Returns:
            str: Path to status.log
        """
        if self._status_log_path is None:
            self._status_log_path = os.path.join(
                self._ai_swarm_dir,
                DEFAULT_STATUS_LOG
            )
        return self._status_log_path

    def _ensure_directory(self) -> None:
        """
        Ensure the AI_SWARM_DIR exists, creating it if necessary.
        """
        os.makedirs(self._ai_swarm_dir, exist_ok=True)

    def _get_timestamp(self) -> str:
        """
        Get current timestamp in ISO 8601 format with milliseconds.

        Returns:
            str: Timestamp like "2026-01-31T12:00:00.000Z"
        """
        now = datetime.now(timezone.utc)
        return now.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

    def _write_atomically(self, line: str) -> None:
        """
        Write a line atomically to the status log.

        Uses file locking (fcntl.flock) to ensure safe concurrent writes
        from multiple workers. Each line is appended to the log file.

        Args:
            line: JSON line to write
        """
        status_log_path = self._get_status_log_path()

        # Ensure directory exists (might be cleaned between calls)
        os.makedirs(os.path.dirname(status_log_path), exist_ok=True)

        with open(status_log_path, 'a') as f:
            # Acquire exclusive lock
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(line + '\n')
                f.flush()
                os.fsync(f.fileno())
            finally:
                # Release lock
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def _broadcast(self, state: BroadcastState, task_id: str,
                   message: str = "", meta: Optional[dict] = None) -> None:
        """
        Internal method to broadcast a status line.

        Args:
            state: BroadcastState value (START, DONE, WAIT, ERROR, HELP, SKIP)
            task_id: Unique task identifier
            message: Optional human-readable message
            meta: Optional dictionary with additional context
        """
        entry = {
            'state': state.value,
            'task_id': task_id,
            'timestamp': self._get_timestamp(),
            'message': message,
        }

        if meta is not None:
            entry['meta'] = meta

        line = json.dumps(entry, ensure_ascii=False)
        self._write_atomically(line)

    def broadcast(self, state: BroadcastState, task_id: str,
                  message: str = "", meta: Optional[dict] = None) -> None:
        """
        Broadcast a status update to the shared log.

        Args:
            state: BroadcastState value (START, DONE, WAIT, ERROR, HELP, SKIP)
            task_id: Unique task identifier
            message: Optional human-readable message
            meta: Optional dictionary with additional context
        """
        self._broadcast(state, task_id, message, meta)

    def broadcast_start(self, task_id: str, message: str = "") -> None:
        """
        Convenience method to broadcast START state.

        Args:
            task_id: Unique task identifier
            message: Optional human-readable message
        """
        self._broadcast(BroadcastState.START, task_id, message)

    def broadcast_done(self, task_id: str, message: str = "") -> None:
        """
        Convenience method to broadcast DONE state.

        Args:
            task_id: Unique task identifier
            message: Optional human-readable message
        """
        self._broadcast(BroadcastState.DONE, task_id, message)

    def broadcast_wait(self, task_id: str, message: str = "") -> None:
        """
        Convenience method to broadcast WAIT state.

        Args:
            task_id: Unique task identifier
            message: Optional human-readable message
        """
        self._broadcast(BroadcastState.WAIT, task_id, message)

    def broadcast_error(self, task_id: str, message: str = "",
                        meta: Optional[dict] = None) -> None:
        """
        Convenience method to broadcast ERROR state.

        Args:
            task_id: Unique task identifier
            message: Optional human-readable message
            meta: Optional dictionary with additional context (e.g., error_type)
        """
        self._broadcast(BroadcastState.ERROR, task_id, message, meta)

    def broadcast_help(self, task_id: str, message: str = "") -> None:
        """
        Convenience method to broadcast HELP state.

        Args:
            task_id: Unique task identifier
            message: Optional human-readable message
        """
        self._broadcast(BroadcastState.HELP, task_id, message)

    def broadcast_skip(self, task_id: str, message: str = "") -> None:
        """
        Convenience method to broadcast SKIP state.

        Args:
            task_id: Unique task identifier
            message: Optional human-readable message
        """
        self._broadcast(BroadcastState.SKIP, task_id, message)

    def __enter__(self):
        """Context manager entry - returns self"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - no cleanup needed"""
        pass
