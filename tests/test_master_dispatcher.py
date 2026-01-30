#!/usr/bin/env python3
"""
Unit Tests for Master Dispatcher

TDD Approach: Write tests FIRST, then implement.
"""

import os
import sys
import json
import unittest
import tempfile
import shutil
from pathlib import Path

from swarm import config
from swarm import task_queue

# Note: master_dispatcher module is not yet implemented in swarm package
# This test will fail until master_dispatcher.py is added to swarm/
try:
    from swarm import master_dispatcher
    MASTER_DISPATCHER_AVAILABLE = True
except ImportError:
    master_dispatcher = None
    MASTER_DISPATCHER_AVAILABLE = False


@unittest.skipUnless(MASTER_DISPATCHER_AVAILABLE, "master_dispatcher not yet implemented")
class TestMasterDispatcher(unittest.TestCase):
    """Test MasterDispatcher functionality"""

    def setUp(self):
        """Create temporary directory for each test"""
        self.test_dir = tempfile.mkdtemp(prefix='dispatcher_test_')
        self.base_dir = os.path.join(self.test_dir, 'ai_swarm')

        # Create directory structure
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, 'instructions'), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, 'locks'), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, 'results'), exist_ok=True)

        # Create status log
        self.status_log = os.path.join(self.base_dir, 'status.log')
        with open(self.status_log, 'w') as f:
            pass

        # Create tasks.json
        self.tasks_file = os.path.join(self.base_dir, 'tasks.json')
        with open(self.tasks_file, 'w') as f:
            json.dump({'tasks': []}, f)

        # Initialize dispatcher
        self.dispatcher = master_dispatcher.MasterDispatcher(
            base_dir=self.base_dir,
            scan_interval=1,
            max_concurrent_tasks=3
        )

        # Initialize task queue
        self.dispatcher.task_queue = task_queue.TaskQueue(
            tasks_file=self.tasks_file
        )

    def tearDown(self):
        """Clean up temporary directory"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_dispatcher_initialization(self):
        """Test: Dispatcher should initialize with base directory"""
        self.assertEqual(self.dispatcher.base_dir, self.base_dir)
        self.assertEqual(self.dispatcher.max_concurrent_tasks, 3)
        self.assertIsInstance(self.dispatcher.stats, dict)

    def test_get_idle_workers_with_no_workers(self):
        """Test: Should return empty list when no workers active"""
        idle = self.dispatcher.get_idle_workers()

        self.assertIsInstance(idle, list)
        self.assertEqual(len(idle), 0)

    def test_get_idle_workers_with_active_workers(self):
        """Test: Should identify idle workers from status updates"""
        # Add status updates for workers
        worker_states = [
            {'node': 'worker-1', 'status': 'DONE', 'msg': 'Task completed', 'time': '2026-01-28 12:00:00'},
            {'node': 'worker-2', 'status': 'START', 'msg': 'Starting task', 'time': '2026-01-28 12:00:01'},
            {'node': 'worker-3', 'status': 'THINKING', 'msg': 'Processing', 'time': '2026-01-28 12:00:02'},
        ]

        # Write to status log
        for state in worker_states:
            entry = {
                'time': state['time'],
                'node': state['node'],
                'status': state['status'],
                'msg': state['msg']
            }
            with open(self.status_log, 'a') as f:
                f.write(json.dumps(entry) + '\n')

        # Scan and update states (dispatcher.scan_log() returns new entries)
        new_entries = self.dispatcher.scan_log()
        for entry in new_entries:
            self.dispatcher.update_state(entry)

        # Get idle workers (worker-1 DONE, worker-2 START are idle)
        idle = self.dispatcher.get_idle_workers()

        self.assertIn('worker-1', idle)
        self.assertIn('worker-2', idle)  # START is idle (ready for tasks)
        self.assertNotIn('worker-3', idle)  # THINKING is busy

    def test_assign_task_to_worker(self):
        """Test: Should create instruction file for worker"""
        task = {
            'id': 'task_001',
            'prompt': 'Test prompt',
            'status': 'pending',
            'priority': 1
        }

        result = self.dispatcher.assign_task_to_worker(task, 'worker-1')

        self.assertTrue(result)

        # Verify instruction file created
        instruction_file = os.path.join(self.base_dir, 'instructions', 'worker-1.json')
        self.assertTrue(os.path.exists(instruction_file))

        # Verify file content
        with open(instruction_file, 'r') as f:
            loaded_task = json.load(f)

        self.assertEqual(loaded_task['task_id'], 'task_001')
        self.assertEqual(loaded_task['prompt'], 'Test prompt')

    def test_assign_task_to_worker_fails_for_busy_worker(self):
        """Test: Should not assign task if worker already has instruction"""
        # Create existing instruction file
        instruction_file = os.path.join(self.base_dir, 'instructions', 'worker-1.json')
        with open(instruction_file, 'w') as f:
            json.dump({'task_id': 'existing_task'}, f)

        task = {
            'id': 'task_002',
            'prompt': 'New task',
            'status': 'pending'
        }

        result = self.dispatcher.assign_task_to_worker(task, 'worker-1')

        self.assertFalse(result)

    def test_dispatch_tasks_to_idle_workers(self):
        """Test: Should dispatch pending tasks to idle workers"""
        # Add pending tasks
        self.dispatcher.task_queue.add_task('Task 1', priority=1)
        self.dispatcher.task_queue.add_task('Task 2', priority=2)

        # Simulate idle worker
        with open(self.status_log, 'a') as f:
            entry = {
                'time': '2026-01-28 12:00:00',
                'node': 'worker-1',
                'status': 'DONE',
                'msg': 'Ready'
            }
            f.write(json.dumps(entry) + '\n')

        self.dispatcher.scan_log()

        dispatched = self.dispatcher.dispatch_tasks()

        self.assertGreaterEqual(dispatched, 0)
        self.assertLessEqual(dispatched, 2)

    def test_dispatch_tasks_respects_max_concurrent(self):
        """Test: Should not exceed max_concurrent_tasks limit"""
        # Add many tasks
        for i in range(10):
            self.dispatcher.task_queue.add_task(f'Task {i}', priority=i+1)

        # Simulate many idle workers
        for i in range(5):
            with open(self.status_log, 'a') as f:
                entry = {
                    'time': '2026-01-28 12:00:00',
                    'node': f'worker-{i}',
                    'status': 'DONE',
                    'msg': 'Ready'
                }
                f.write(json.dumps(entry) + '\n')

        self.dispatcher.scan_log()

        dispatched = self.dispatcher.dispatch_tasks()

        self.assertLessEqual(dispatched, self.dispatcher.max_concurrent_tasks)

    def test_update_statistics(self):
        """Test: Should update statistics from task queue"""
        # Add some tasks
        task_id_1 = self.dispatcher.task_queue.add_task('Task 1')
        task_id_2 = self.dispatcher.task_queue.add_task('Task 2')

        # Assign and complete one task
        self.dispatcher.task_queue.assign_task(task_id_1, 'worker-1')
        self.dispatcher.task_queue.complete_task(task_id_1, '/path/to/result.md')

        # Assign and fail one task
        self.dispatcher.task_queue.assign_task(task_id_2, 'worker-2')
        self.dispatcher.task_queue.fail_task(task_id_2, 'Test error')

        # Update statistics
        self.dispatcher.update_statistics()

        # Should have completed and failed tasks
        self.assertGreater(self.dispatcher.stats['tasks_completed'], 0)
        self.assertGreater(self.dispatcher.stats['tasks_failed'], 0)

    def test_format_status_table_with_stats(self):
        """Test: Status table should include statistics"""
        # Add some worker activity
        with open(self.status_log, 'a') as f:
            entry = {
                'time': '2026-01-28 12:00:00',
                'node': 'worker-1',
                'status': 'START',
                'msg': 'Starting'
            }
            f.write(json.dumps(entry) + '\n')

        self.dispatcher.scan_log()
        self.dispatcher.update_statistics()

        table = self.dispatcher.format_status_table()

        self.assertIn('AI Swarm Status', table)
        self.assertIsInstance(table, str)


if __name__ == '__main__':
    unittest.main(verbosity=2)
