#!/usr/bin/env python3
"""
Test suite for task_lock.py
Phase 3: Shared State System - Task Lock Manager Tests

Uses isolated_swarm_dir fixture from conftest.py for test isolation.
"""

import json
import os
import time
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from swarm import task_lock


class TestTaskLockManager(unittest.TestCase):
    """Test suite for TaskLockManager"""

    def test_acquire_lock_creates_lock_file(self):
        """Test: acquire_lock should create lock file"""
        tl = task_lock.TaskLockManager('worker-1')
        result = tl.acquire_lock('task-001')

        lock_path = tl._get_lock_path('task-001')
        self.assertTrue(result)
        self.assertTrue(os.path.exists(lock_path))

    def test_acquire_lock_returns_true_on_success(self):
        """Test: acquire_lock returns True on successful acquisition"""
        tl = task_lock.TaskLockManager('worker-1')
        result = tl.acquire_lock('task-001')

        self.assertTrue(result)

    def test_acquire_lock_returns_false_if_locked(self):
        """Test: acquire_lock returns False if lock is held by another worker"""
        tl1 = task_lock.TaskLockManager('worker-1')
        tl2 = task_lock.TaskLockManager('worker-2')

        # Worker-1 acquires
        tl1.acquire_lock('task-001')

        # Worker-2 tries to acquire same task
        result = tl2.acquire_lock('task-001')

        self.assertFalse(result)

    def test_acquire_lock_idempotent_for_same_worker(self):
        """Test: acquire_lock returns True if lock already owned by same worker"""
        tl = task_lock.TaskLockManager('worker-1')

        first = tl.acquire_lock('task-001')
        second = tl.acquire_lock('task-001')

        self.assertTrue(first)
        self.assertTrue(second)

        info = tl.get_lock_info('task-001')
        self.assertEqual(info.worker_id, 'worker-1')

    def test_acquire_lock_allows_reacquire_after_expired(self):
        """Test: acquire_lock allows reacquisition after lock expires"""
        tl1 = task_lock.TaskLockManager('worker-1')
        tl2 = task_lock.TaskLockManager('worker-2')

        # Worker-1 acquires lock
        tl1.acquire_lock('task-001')

        # Manually create expired lock file
        lock_path = tl1._get_lock_path('task-001')
        expired_info = task_lock.LockInfo(
            worker_id='worker-old',
            task_id='task-001',
            acquired_at='2020-01-01T00:00:00.000Z',
            heartbeat_at='2020-01-01T00:00:00.000Z',
            ttl=300
        )
        with open(lock_path, 'w') as f:
            f.write(expired_info.to_json())

        # Worker-2 should be able to acquire (expired lock)
        result = tl2.acquire_lock('task-001')
        self.assertTrue(result)

        # Verify new lock has correct worker_id
        info = tl2.get_lock_info('task-001')
        self.assertEqual(info.worker_id, 'worker-2')

    def test_release_lock_deletes_file(self):
        """Test: release_lock should delete the lock file"""
        tl = task_lock.TaskLockManager('worker-1')

        tl.acquire_lock('task-001')
        self.assertTrue(os.path.exists(tl._get_lock_path('task-001')))

        tl.release_lock('task-001')
        self.assertFalse(os.path.exists(tl._get_lock_path('task-001')))

    def test_release_lock_returns_true_if_owned(self):
        """Test: release_lock returns True when worker owns the lock"""
        tl = task_lock.TaskLockManager('worker-1')

        tl.acquire_lock('task-001')
        result = tl.release_lock('task-001')

        self.assertTrue(result)

    def test_release_lock_returns_false_if_not_owned(self):
        """Test: release_lock returns False if worker doesn't own the lock"""
        tl1 = task_lock.TaskLockManager('worker-1')
        tl2 = task_lock.TaskLockManager('worker-2')

        tl1.acquire_lock('task-001')
        result = tl2.release_lock('task-001')

        self.assertFalse(result)

    def test_update_heartbeat(self):
        """Test: update_heartbeat should update the heartbeat timestamp"""
        tl = task_lock.TaskLockManager('worker-1')

        tl.acquire_lock('task-001')
        info_before = tl.get_lock_info('task-001')

        # Small delay to ensure timestamp difference
        time.sleep(0.01)

        tl.update_heartbeat('task-001')
        info_after = tl.get_lock_info('task-001')

        self.assertGreater(info_after.heartbeat_at, info_before.heartbeat_at)

    def test_update_heartbeat_fails_if_not_owned(self):
        """Test: update_heartbeat returns False if worker doesn't own lock"""
        tl1 = task_lock.TaskLockManager('worker-1')
        tl2 = task_lock.TaskLockManager('worker-2')

        tl1.acquire_lock('task-001')
        result = tl2.update_heartbeat('task-001')

        self.assertFalse(result)

    def test_is_locked_true_when_locked(self):
        """Test: is_locked returns True when task is locked"""
        tl = task_lock.TaskLockManager('worker-1')

        tl.acquire_lock('task-001')
        result = tl.is_locked('task-001')

        self.assertTrue(result)

    def test_is_locked_false_when_not_locked(self):
        """Test: is_locked returns False when task is not locked"""
        tl = task_lock.TaskLockManager('worker-1')

        result = tl.is_locked('task-nonexistent')

        self.assertFalse(result)

    def test_get_lock_info(self):
        """Test: get_lock_info returns correct lock information"""
        tl = task_lock.TaskLockManager('worker-1')

        tl.acquire_lock('task-001')
        info = tl.get_lock_info('task-001')

        self.assertIsNotNone(info)
        self.assertEqual(info.worker_id, 'worker-1')
        self.assertEqual(info.task_id, 'task-001')
        self.assertEqual(info.ttl, 300)

    def test_get_lock_info_returns_none_if_not_exist(self):
        """Test: get_lock_info returns None if task is not locked"""
        tl = task_lock.TaskLockManager('worker-1')

        info = tl.get_lock_info('task-nonexistent')

        self.assertIsNone(info)

    def test_is_expired_within_ttl(self):
        """Test: is_expired returns False when within TTL"""
        tl = task_lock.TaskLockManager('worker-1')

        tl.acquire_lock('task-001')
        info = tl.get_lock_info('task-001')

        self.assertFalse(tl.is_expired(info))

    def test_is_expired_past_ttl(self):
        """Test: is_expired returns True when past TTL"""
        tl = task_lock.TaskLockManager('worker-1')

        # Create lock with old heartbeat
        lock_path = tl._get_lock_path('task-001')
        os.makedirs(os.path.dirname(lock_path), exist_ok=True)
        old_info = task_lock.LockInfo(
            worker_id='worker-1',
            task_id='task-001',
            acquired_at='2020-01-01T00:00:00.000Z',
            heartbeat_at='2020-01-01T00:04:00.000Z',  # 4 minutes ago
            ttl=300  # 5 minutes TTL
        )
        with open(lock_path, 'w') as f:
            f.write(old_info.to_json())

        info = tl.get_lock_info('task-001')
        self.assertTrue(tl.is_expired(info))

    def test_lock_content_json_format(self):
        """Test: lock file contains correct JSON format"""
        tl = task_lock.TaskLockManager('worker-1')

        tl.acquire_lock('task-001')
        lock_path = tl._get_lock_path('task-001')

        with open(lock_path, 'r') as f:
            content = f.read()

        # Should be valid JSON
        data = json.loads(content)

        # Should have all required fields
        self.assertIn('worker_id', data)
        self.assertIn('task_id', data)
        self.assertIn('acquired_at', data)
        self.assertIn('heartbeat_at', data)
        self.assertIn('ttl', data)

        # Values should match
        self.assertEqual(data['worker_id'], 'worker-1')
        self.assertEqual(data['task_id'], 'task-001')
        self.assertEqual(data['ttl'], 300)

    def test_ttl_env_override(self):
        """Test: TTL can be overridden via environment variable"""
        import shutil
        base_dir = '/tmp/test_swarm_ttl'
        if os.path.exists(base_dir):
            shutil.rmtree(base_dir)

        os.environ['AI_SWARM_LOCK_TTL'] = '600'
        try:
            tl = task_lock.TaskLockManager('worker-1')
            self.assertEqual(tl._ttl, 600)
        finally:
            del os.environ['AI_SWARM_LOCK_TTL']
            if os.path.exists(base_dir):
                shutil.rmtree(base_dir)

    def test_convenience_methods(self):
        """Test: acquire and release work correctly"""
        tl = task_lock.TaskLockManager('worker-1')

        # Acquire
        acquired = tl.acquire_lock('task-001')
        self.assertTrue(acquired)
        self.assertTrue(tl.is_locked('task-001'))

        # Release
        released = tl.release_lock('task-001')
        self.assertTrue(released)
        self.assertFalse(tl.is_locked('task-001'))

    def test_cleanup_expired_locks(self):
        """Test: cleanup_expired_locks removes expired locks"""
        tl = task_lock.TaskLockManager('worker-1')

        # Create an expired lock file manually
        os.makedirs(tl._get_locks_dir(), exist_ok=True)
        expired_lock_path = os.path.join(tl._get_locks_dir(), 'task-expired.lock')
        expired_info = task_lock.LockInfo(
            worker_id='worker-old',
            task_id='task-expired',
            acquired_at='2020-01-01T00:00:00.000Z',
            heartbeat_at='2020-01-01T00:00:00.000Z',
            ttl=300
        )
        with open(expired_lock_path, 'w') as f:
            f.write(expired_info.to_json())

        # Also create a valid lock
        tl.acquire_lock('task-valid')

        # Cleanup
        cleaned = tl.cleanup_expired_locks()

        # Should have cleaned 1 expired lock
        self.assertEqual(cleaned, 1)

        # Expired lock should be gone
        self.assertFalse(os.path.exists(expired_lock_path))

        # Valid lock should still exist
        self.assertTrue(os.path.exists(tl._get_lock_path('task-valid')))

    def test_multiple_locks_same_worker(self):
        """Test: same worker can acquire multiple different locks"""
        tl = task_lock.TaskLockManager('worker-1')

        result1 = tl.acquire_lock('task-001')
        result2 = tl.acquire_lock('task-002')
        result3 = tl.acquire_lock('task-003')

        self.assertTrue(result1)
        self.assertTrue(result2)
        self.assertTrue(result3)

        self.assertTrue(tl.is_locked('task-001'))
        self.assertTrue(tl.is_locked('task-002'))
        self.assertTrue(tl.is_locked('task-003'))


class TestLockInfo(unittest.TestCase):
    """Test suite for LockInfo dataclass"""

    def test_create_sets_timestamps(self):
        """Test: LockInfo.create sets timestamps correctly"""
        info = task_lock.LockInfo.create('worker-1', 'task-001', 300)

        self.assertEqual(info.worker_id, 'worker-1')
        self.assertEqual(info.task_id, 'task-001')
        self.assertEqual(info.ttl, 300)
        self.assertIsNotNone(info.acquired_at)
        self.assertIsNotNone(info.heartbeat_at)
        self.assertIn('T', info.acquired_at)  # ISO 8601 format contains T
        self.assertIn('T', info.heartbeat_at)  # ISO 8601 format contains T

    def test_to_json(self):
        """Test: to_json serializes correctly"""
        info = task_lock.LockInfo.create('worker-1', 'task-001', 300)
        json_str = info.to_json()

        data = json.loads(json_str)
        self.assertEqual(data['worker_id'], 'worker-1')
        self.assertEqual(data['task_id'], 'task-001')
        self.assertEqual(data['ttl'], 300)

    def test_from_json(self):
        """Test: from_json deserializes correctly"""
        json_str = '{"worker_id": "worker-1", "task_id": "task-001", "acquired_at": "2026-01-31T12:00:00.000Z", "heartbeat_at": "2026-01-31T12:00:00.000Z", "ttl": 300}'
        info = task_lock.LockInfo.from_json(json_str)

        self.assertEqual(info.worker_id, 'worker-1')
        self.assertEqual(info.task_id, 'task-001')
        self.assertEqual(info.ttl, 300)

    def test_is_expired_false_when_fresh(self):
        """Test: is_expired returns False for fresh lock"""
        info = task_lock.LockInfo.create('worker-1', 'task-001', 300)
        self.assertFalse(info.is_expired())

    def test_is_expired_true_when_old(self):
        """Test: is_expired returns True for old lock"""
        info = task_lock.LockInfo(
            worker_id='worker-1',
            task_id='task-001',
            acquired_at='2020-01-01T00:00:00.000Z',
            heartbeat_at='2020-01-01T00:00:00.000Z',
            ttl=300
        )
        self.assertTrue(info.is_expired())


if __name__ == '__main__':
    unittest.main(verbosity=2)
