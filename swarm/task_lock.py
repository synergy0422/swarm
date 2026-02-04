#!/usr/bin/env python3
"""
Task Lock Manager Module for AI Swarm System

Provides atomic task locking using file creation (O_CREAT|O_EXCL) for
multi-agent coordination. Prevents duplicate task execution across workers.
"""

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional


# Default configuration
DEFAULT_LOCKS_DIR = 'locks'
DEFAULT_AI_SWARM_DIR = '/tmp/ai_swarm'
DEFAULT_LOCK_TTL = 300  # 5 minutes in seconds
DEFAULT_HEARTBEAT_INTERVAL = 10  # 10 seconds

# Environment variable names
ENV_AI_SWARM_DIR = 'AI_SWARM_DIR'
ENV_LOCK_TTL = 'AI_SWARM_LOCK_TTL'


def get_ai_swarm_dir() -> str:
    """
    Get AI_SWARM_DIR from environment variable or use default.

    Returns:
        str: Path to AI Swarm directory
    """
    return os.environ.get(ENV_AI_SWARM_DIR, DEFAULT_AI_SWARM_DIR)


def get_lock_ttl() -> int:
    """
    Get lock TTL from environment variable or use default.

    Returns:
        int: TTL in seconds (default 300 = 5 minutes)
    """
    ttl_str = os.environ.get(ENV_LOCK_TTL)
    if ttl_str:
        try:
            return int(ttl_str)
        except ValueError:
            pass
    return DEFAULT_LOCK_TTL


@dataclass
class LockInfo:
    """
    Represents task lock information.

    Attributes:
        worker_id: ID of the worker holding the lock
        task_id: ID of the locked task
        acquired_at: ISO 8601 timestamp when lock was acquired
        heartbeat_at: ISO 8601 timestamp of last heartbeat
        ttl: Time-to-live in seconds
    """
    worker_id: str
    task_id: str
    acquired_at: str
    heartbeat_at: str
    ttl: int

    @classmethod
    def create(cls, worker_id: str, task_id: str, ttl: int) -> 'LockInfo':
        """
        Create a new LockInfo with current timestamps.

        Args:
            worker_id: ID of the worker acquiring the lock
            task_id: ID of the task being locked
            ttl: Time-to-live in seconds

        Returns:
            LockInfo: New lock info instance
        """
        now = datetime.now(timezone.utc)
        timestamp = now.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

        return cls(
            worker_id=worker_id,
            task_id=task_id,
            acquired_at=timestamp,
            heartbeat_at=timestamp,
            ttl=ttl
        )

    def to_json(self) -> str:
        """Serialize lock info to JSON string with backward compatibility"""
        data = asdict(self)
        # Write both ttl_sec and ttl for backward compatibility
        data['ttl_sec'] = self.ttl
        data['ttl'] = self.ttl
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'LockInfo':
        """Deserialize lock info from JSON string with backward compatibility"""
        data = json.loads(json_str)
        # Prefer ttl_sec, fallback to ttl for backward compatibility
        ttl_value = data.get('ttl_sec') or data.get('ttl', DEFAULT_LOCK_TTL)
        # Remove ttl_sec from data to avoid unexpected keyword argument
        data.pop('ttl_sec', None)
        data['ttl'] = ttl_value
        return cls(**data)

    def is_expired(self) -> bool:
        """
        Check if the lock has expired based on heartbeat_at + ttl.

        Returns:
            bool: True if lock is expired, False otherwise
        """
        heartbeat = datetime.fromisoformat(self.heartbeat_at.replace('Z', '+00:00'))
        # Use UTC for consistency
        now = datetime.now(timezone.utc)
        # Make heartbeat UTC-aware for comparison
        heartbeat_utc = heartbeat.replace(tzinfo=timezone.utc)
        return (now - heartbeat_utc).total_seconds() > self.ttl


class TaskLockManager:
    """
    Manages atomic task locks using file-based locking.

    Uses O_CREAT|O_EXCL for atomic lock acquisition, avoiding fcntl.flock
    which has platform-specific behavior. Lock files are stored in:
    {AI_SWARM_DIR}/locks/{task_id}.lock

    Lock content is JSON with worker_id, task_id, acquired_at, heartbeat_at, ttl.

    Lock Competition Behavior:
    - If lock exists and is expired: delete old lock, allow new acquisition
    - If lock exists and is not expired: fast fail (return False)
    - If lock doesn't exist: atomically create new lock

    Heartbeat:
    - Workers should call update_heartbeat() every 10 seconds while holding lock
    - Updates the heartbeat_at timestamp to prevent expiration
    """

    def __init__(self, worker_id: str):
        """
        Initialize TaskLockManager with worker ID.

        Args:
            worker_id: Unique identifier for this worker
        """
        self.worker_id = worker_id
        self._ai_swarm_dir = get_ai_swarm_dir()
        self._locks_dir = None
        self._ttl = get_lock_ttl()
        self._ensure_directories()

    def _get_locks_dir(self) -> str:
        """
        Get the locks directory path.

        Returns:
            str: Path to locks directory
        """
        if self._locks_dir is None:
            self._locks_dir = os.path.join(
                self._ai_swarm_dir,
                DEFAULT_LOCKS_DIR
            )
        return self._locks_dir

    def _get_lock_path(self, task_id: str) -> str:
        """
        Get the lock file path for a task.

        Args:
            task_id: Task identifier

        Returns:
            str: Path to lock file
        """
        return os.path.join(self._get_locks_dir(), f'{task_id}.lock')

    def _get_ttl(self) -> int:
        """
        Get the lock TTL.

        Returns:
            int: TTL in seconds
        """
        return self._ttl

    def _ensure_directories(self) -> None:
        """
        Ensure the locks directory exists.
        """
        os.makedirs(self._get_locks_dir(), exist_ok=True)

    def _get_timestamp(self) -> str:
        """
        Get current timestamp in ISO 8601 format with milliseconds.

        Returns:
            str: Timestamp like "2026-01-31T12:00:00.000Z"
        """
        now = datetime.now(timezone.utc)
        return now.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

    def _is_lock_expired(self, lock_info: LockInfo) -> bool:
        """
        Check if a lock is expired.

        Args:
            lock_info: LockInfo to check

        Returns:
            bool: True if expired, False otherwise
        """
        return lock_info.is_expired()

    def acquire_lock(self, task_id: str) -> bool:
        """
        Atomically acquire a lock for the specified task.

        Lock Competition:
        - If lock file doesn't exist: atomically create it, return True
        - If lock exists but is expired: delete it, create new, return True
        - If lock exists and is not expired: return False (fast fail)

        Args:
            task_id: Task to acquire lock for

        Returns:
            bool: True if lock acquired, False if already locked
        """
        lock_path = self._get_lock_path(task_id)

        # Check if lock file exists
        if os.path.exists(lock_path):
            try:
                with open(lock_path, 'r') as f:
                    lock_data = f.read()
                    lock_info = LockInfo.from_json(lock_data)

                # Check if expired
                if self._is_lock_expired(lock_info):
                    # Lazy cleanup: delete expired lock
                    try:
                        os.unlink(lock_path)
                    except OSError:
                        # Lock might have been deleted by another worker
                        pass
                else:
                    # Lock is held by another worker (or self)
                    if lock_info.worker_id == self.worker_id:
                        # Idempotent acquire: already owned by this worker
                        return True
                    return False
            except (json.JSONDecodeError, KeyError, FileNotFoundError):
                # Corrupted or missing lock file, try to create new one
                pass

        # Try to atomically create the lock file
        lock_info = LockInfo.create(self.worker_id, task_id, self._get_ttl())

        try:
            # Atomic file creation using O_CREAT | O_EXCL
            flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
            fd = os.open(lock_path, flags, 0o644)
            with os.fdopen(fd, 'w') as f:
                f.write(lock_info.to_json())
            return True
        except FileExistsError:
            # Another worker beat us to it
            return False

    def release_lock(self, task_id: str) -> bool:
        """
        Release a lock held by this worker.

        Only releases if this worker owns the lock.

        Args:
            task_id: Task to release lock for

        Returns:
            bool: True if lock was released, False if not owned or not exist
        """
        lock_path = self._get_lock_path(task_id)

        if not os.path.exists(lock_path):
            return False

        try:
            with open(lock_path, 'r') as f:
                lock_data = f.read()
                lock_info = LockInfo.from_json(lock_data)

            # Check ownership
            if lock_info.worker_id != self.worker_id:
                return False

            # Delete the lock file
            os.unlink(lock_path)
            return True

        except (json.JSONDecodeError, KeyError, FileNotFoundError, OSError):
            return False

    def update_heartbeat(self, task_id: str) -> bool:
        """
        Update the heartbeat timestamp for a lock.

        Called periodically (every 10 seconds) by the worker holding the lock.

        Args:
            task_id: Task to update heartbeat for

        Returns:
            bool: True if heartbeat updated, False if not owned or not exist
        """
        lock_path = self._get_lock_path(task_id)

        if not os.path.exists(lock_path):
            return False

        try:
            with open(lock_path, 'r') as f:
                lock_data = f.read()
                lock_info = LockInfo.from_json(lock_data)

            # Check ownership
            if lock_info.worker_id != self.worker_id:
                return False

            # Update heartbeat timestamp
            lock_info.heartbeat_at = self._get_timestamp()

            # Write atomically (temp file + rename)
            temp_path = lock_path + '.tmp'
            with open(temp_path, 'w') as f:
                f.write(lock_info.to_json())
            os.replace(temp_path, lock_path)

            return True

        except (json.JSONDecodeError, KeyError, FileNotFoundError, OSError):
            return False

    def is_locked(self, task_id: str) -> bool:
        """
        Check if a task is currently locked.

        Args:
            task_id: Task to check

        Returns:
            bool: True if locked (by any worker), False otherwise
        """
        lock_path = self._get_lock_path(task_id)

        if not os.path.exists(lock_path):
            return False

        try:
            with open(lock_path, 'r') as f:
                lock_data = f.read()
                lock_info = LockInfo.from_json(lock_data)
                return not self._is_lock_expired(lock_info)
        except (json.JSONDecodeError, KeyError, FileNotFoundError):
            return False

    def get_lock_info(self, task_id: str) -> Optional[LockInfo]:
        """
        Get lock information for a task.

        Args:
            task_id: Task to get lock info for

        Returns:
            LockInfo: Lock information if locked, None if not exist
        """
        lock_path = self._get_lock_path(task_id)

        if not os.path.exists(lock_path):
            return None

        try:
            with open(lock_path, 'r') as f:
                lock_data = f.read()
                return LockInfo.from_json(lock_data)
        except (json.JSONDecodeError, KeyError, FileNotFoundError):
            return None

    def is_expired(self, lock: LockInfo) -> bool:
        """
        Check if a lock info is expired.

        Args:
            lock: LockInfo to check

        Returns:
            bool: True if expired, False otherwise
        """
        return lock.is_expired()

    def cleanup_expired_locks(self) -> int:
        """
        Clean up all expired locks in the locks directory.

        Returns:
            int: Number of locks cleaned up
        """
        cleaned = 0
        locks_dir = self._get_locks_dir()

        if not os.path.exists(locks_dir):
            return 0

        try:
            for filename in os.listdir(locks_dir):
                if filename.endswith('.lock'):
                    lock_path = os.path.join(locks_dir, filename)
                    try:
                        with open(lock_path, 'r') as f:
                            lock_data = f.read()
                            lock_info = LockInfo.from_json(lock_data)

                        if self._is_lock_expired(lock_info):
                            os.unlink(lock_path)
                            cleaned += 1
                    except (json.JSONDecodeError, KeyError, FileNotFoundError, OSError):
                        # Corrupted lock file, delete it
                        try:
                            os.unlink(lock_path)
                            cleaned += 1
                        except OSError:
                            pass
        except OSError:
            pass

        return cleaned
