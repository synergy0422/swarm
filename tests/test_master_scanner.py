#!/usr/bin/env python3
"""
Test suite for master_scanner.py
Phase 4: Master Implementation - Master Scanner Tests

Uses isolated_swarm_dir fixture from conftest.py for test isolation.
"""

import os
import json
import unittest
import time


class TestMasterScanner(unittest.TestCase):
    """Test suite for MasterScanner"""

    def test_read_worker_status_empty_log(self):
        """Test: read_worker_status handles empty status.log"""
        from swarm import master_scanner

        scanner = master_scanner.MasterScanner('cluster-test')
        statuses = scanner.read_worker_status()

        self.assertEqual(len(statuses), 0)
        self.assertIsInstance(statuses, list)

    def test_read_worker_status_single_entry(self):
        """Test: read_worker_status parses single JSONL line"""
        from swarm import master_scanner

        scanner = master_scanner.MasterScanner('cluster-test')

        # Write a single status entry
        status_entry = {
            'ts': '2026-01-31T12:00:00.000Z',
            'worker_id': 'worker-1',
            'task_id': 'task-001',
            'state': 'START',
            'message': 'Starting task'
        }

        status_path = scanner._get_status_log_path()
        with open(status_path, 'w') as f:
            f.write(json.dumps(status_entry) + '\n')

        # Read worker status
        statuses = scanner.read_worker_status()

        self.assertEqual(len(statuses), 1)
        self.assertEqual(statuses[0].worker_id, 'worker-1')
        self.assertEqual(statuses[0].state, 'START')
        self.assertEqual(statuses[0].task_id, 'task-001')
        self.assertEqual(statuses[0].message, 'Starting task')
        self.assertEqual(statuses[0].timestamp, '2026-01-31T12:00:00.000Z')

    def test_read_worker_status_multiple_workers(self):
        """Test: read_worker_status returns last status per worker"""
        from swarm import master_scanner

        scanner = master_scanner.MasterScanner('cluster-test')

        # Write multiple status entries for multiple workers
        entries = [
            {
                'ts': '2026-01-31T12:00:00.000Z',
                'worker_id': 'worker-1',
                'task_id': 'task-001',
                'state': 'START',
                'message': 'Worker 1 starting'
            },
            {
                'ts': '2026-01-31T12:00:01.000Z',
                'worker_id': 'worker-2',
                'task_id': 'task-002',
                'state': 'DONE',
                'message': 'Worker 2 done'
            },
            {
                'ts': '2026-01-31T12:00:02.000Z',
                'worker_id': 'worker-1',
                'task_id': 'task-001',
                'state': 'DONE',
                'message': 'Worker 1 done'
            },
        ]

        status_path = scanner._get_status_log_path()
        with open(status_path, 'w') as f:
            for entry in entries:
                f.write(json.dumps(entry) + '\n')

        # Read worker status
        statuses = scanner.read_worker_status()

        self.assertEqual(len(statuses), 2)

        # Create a dict for easier verification
        status_by_worker = {s.worker_id: s for s in statuses}

        # Verify worker-1 has the last status (DONE)
        self.assertEqual(status_by_worker['worker-1'].state, 'DONE')
        self.assertEqual(status_by_worker['worker-1'].message, 'Worker 1 done')

        # Verify worker-2 has the correct status
        self.assertEqual(status_by_worker['worker-2'].state, 'DONE')
        self.assertEqual(status_by_worker['worker-2'].message, 'Worker 2 done')

    def test_read_lock_state_nonexistent(self):
        """Test: read_lock_state returns None for unlocked task"""
        from swarm import master_scanner

        scanner = master_scanner.MasterScanner('cluster-test')

        # Check a task that doesn't have a lock
        lock_info = scanner.read_lock_state('nonexistent-task')

        self.assertIsNone(lock_info)

    def test_read_lock_state_locked(self):
        """Test: read_lock_state returns LockInfo for locked task"""
        from swarm import master_scanner, task_lock

        # Create a TaskLockManager to acquire a lock
        lock_manager = task_lock.TaskLockManager(worker_id='worker-1')
        acquired = lock_manager.acquire_lock('task-locked')

        self.assertTrue(acquired, 'Lock should be acquired')

        # Now use MasterScanner to read the lock state
        scanner = master_scanner.MasterScanner('cluster-test')
        lock_info = scanner.read_lock_state('task-locked')

        self.assertIsNotNone(lock_info)
        self.assertEqual(lock_info.worker_id, 'worker-1')
        self.assertEqual(lock_info.task_id, 'task-locked')
        self.assertIsInstance(lock_info, task_lock.LockInfo)

        # Cleanup
        lock_manager.release_lock('task-locked')

    def test_get_poll_interval_default(self):
        """Test: get_poll_interval returns 1.0 when env not set"""
        from swarm import master_scanner

        # Remove the env var if it exists
        import os
        old_val = os.environ.pop('AI_SWARM_POLL_INTERVAL', None)

        try:
            interval = master_scanner.get_poll_interval()
            self.assertEqual(interval, 1.0)
        finally:
            # Restore old value if it existed
            if old_val is not None:
                os.environ['AI_SWARM_POLL_INTERVAL'] = old_val

    def test_get_poll_interval_custom(self):
        """Test: get_poll_interval returns env value when set"""
        from swarm import master_scanner
        import os

        old_val = os.environ.get('AI_SWARM_POLL_INTERVAL')
        os.environ['AI_SWARM_POLL_INTERVAL'] = '2.5'

        try:
            interval = master_scanner.get_poll_interval()
            self.assertEqual(interval, 2.5)
        finally:
            if old_val is None:
                os.environ.pop('AI_SWARM_POLL_INTERVAL', None)
            else:
                os.environ['AI_SWARM_POLL_INTERVAL'] = old_val

    def test_worker_status_dataclass(self):
        """Test: WorkerStatus dataclass has correct fields"""
        from swarm import master_scanner

        status = master_scanner.WorkerStatus(
            worker_id='worker-1',
            state='RUNNING',
            task_id='task-001',
            timestamp='2026-01-31T12:00:00.000Z',
            message='Test message'
        )

        self.assertEqual(status.worker_id, 'worker-1')
        self.assertEqual(status.state, 'RUNNING')
        self.assertEqual(status.task_id, 'task-001')
        self.assertEqual(status.timestamp, '2026-01-31T12:00:00.000Z')
        self.assertEqual(status.message, 'Test message')

    def test_scan_all_returns_dict(self):
        """Test: scan_all returns dict of worker_id to WorkerStatus"""
        from swarm import master_scanner

        scanner = master_scanner.MasterScanner('cluster-test')

        # Write a status entry
        status_entry = {
            'ts': '2026-01-31T12:00:00.000Z',
            'worker_id': 'worker-1',
            'task_id': 'task-001',
            'state': 'START',
            'message': 'Starting'
        }

        status_path = scanner._get_status_log_path()
        with open(status_path, 'w') as f:
            f.write(json.dumps(status_entry) + '\n')

        # Scan all workers
        result = scanner.scan_all()

        self.assertIsInstance(result, dict)
        self.assertIn('worker-1', result)
        self.assertEqual(result['worker-1'].worker_id, 'worker-1')

    def test_read_worker_status_malformed_lines(self):
        """Test: read_worker_status skips malformed JSON lines"""
        from swarm import master_scanner

        scanner = master_scanner.MasterScanner('cluster-test')

        # Write mix of valid and invalid entries
        status_path = scanner._get_status_log_path()
        with open(status_path, 'w') as f:
            # Valid entry
            f.write(json.dumps({
                'ts': '2026-01-31T12:00:00.000Z',
                'worker_id': 'worker-1',
                'task_id': 'task-001',
                'state': 'START',
                'message': 'Valid'
            }) + '\n')
            # Invalid JSON
            f.write('this is not json\n')
            # Another valid entry
            f.write(json.dumps({
                'ts': '2026-01-31T12:00:01.000Z',
                'worker_id': 'worker-2',
                'task_id': 'task-002',
                'state': 'DONE',
                'message': 'Also valid'
            }) + '\n')

        # Read worker status
        statuses = scanner.read_worker_status()

        # Should return 2 valid entries, skip the malformed one
        self.assertEqual(len(statuses), 2)
        worker_ids = {s.worker_id for s in statuses}
        self.assertEqual(worker_ids, {'worker-1', 'worker-2'})

    def test_read_worker_status_empty_lines(self):
        """Test: read_worker_status skips empty lines"""
        from swarm import master_scanner

        scanner = master_scanner.MasterScanner('cluster-test')

        # Write entries with empty lines
        status_path = scanner._get_status_log_path()
        with open(status_path, 'w') as f:
            f.write('\n')
            f.write(json.dumps({
                'ts': '2026-01-31T12:00:00.000Z',
                'worker_id': 'worker-1',
                'task_id': 'task-001',
                'state': 'START',
                'message': 'Valid'
            }) + '\n')
            f.write('\n')
            f.write('   \n')  # Whitespace-only line

        # Read worker status
        statuses = scanner.read_worker_status()

        # Should return 1 entry, skip empty lines
        self.assertEqual(len(statuses), 1)
        self.assertEqual(statuses[0].worker_id, 'worker-1')

    def test_create_scanner_factory(self):
        """Test: create_scanner factory function works"""
        from swarm import master_scanner

        scanner = master_scanner.create_scanner('test-cluster')

        self.assertIsInstance(scanner, master_scanner.MasterScanner)
        self.assertEqual(scanner.cluster_id, 'test-cluster')


if __name__ == '__main__':
    unittest.main(verbosity=2)
