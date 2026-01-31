#!/usr/bin/env python3
"""
Test suite for status_broadcaster.py
Phase 3: Shared State System - Status Broadcasting Tests

Uses isolated_swarm_dir fixture from conftest.py for test isolation.
"""

import os
import json
import unittest


class TestStatusBroadcaster(unittest.TestCase):
    """Test suite for StatusBroadcaster"""

    def test_broadcast_start_creates_jsonl_line(self):
        """Test: broadcast_start should create proper START state line"""
        from swarm import status_broadcaster

        sb = status_broadcaster.StatusBroadcaster('worker-1')
        sb.broadcast_start('task-001', 'Starting task')

        status_path = os.path.join(sb._ai_swarm_dir, 'status.log')
        self.assertTrue(os.path.exists(status_path))

        with open(status_path) as f:
            line = f.readline().strip()

        entry = json.loads(line)
        self.assertEqual(entry['state'], 'START')
        self.assertEqual(entry['task_id'], 'task-001')
        self.assertEqual(entry['message'], 'Starting task')
        self.assertIn('ts', entry)
        self.assertIn('worker_id', entry)

    def test_broadcast_done_creates_jsonl_line(self):
        """Test: broadcast_done should create proper DONE state line"""
        from swarm import status_broadcaster

        sb = status_broadcaster.StatusBroadcaster('worker-1')
        sb.broadcast_done('task-001', 'Task completed')

        status_path = os.path.join(sb._ai_swarm_dir, 'status.log')
        with open(status_path) as f:
            line = f.readline().strip()

        entry = json.loads(line)
        self.assertEqual(entry['state'], 'DONE')
        self.assertEqual(entry['task_id'], 'task-001')
        self.assertEqual(entry['message'], 'Task completed')

    def test_broadcast_wait_creates_jsonl_line(self):
        """Test: broadcast_wait should create proper WAIT state line"""
        from swarm import status_broadcaster

        sb = status_broadcaster.StatusBroadcaster('worker-1')
        sb.broadcast_wait('task-001', 'Waiting for input')

        status_path = os.path.join(sb._ai_swarm_dir, 'status.log')
        with open(status_path) as f:
            line = f.readline().strip()

        entry = json.loads(line)
        self.assertEqual(entry['state'], 'WAIT')
        self.assertEqual(entry['task_id'], 'task-001')

    def test_broadcast_error_creates_jsonl_line(self):
        """Test: broadcast_error should create proper ERROR state line"""
        from swarm import status_broadcaster

        sb = status_broadcaster.StatusBroadcaster('worker-1')
        sb.broadcast_error('task-001', 'Failed', {'error_type': 'timeout'})

        status_path = os.path.join(sb._ai_swarm_dir, 'status.log')
        with open(status_path) as f:
            line = f.readline().strip()

        entry = json.loads(line)
        self.assertEqual(entry['state'], 'ERROR')
        self.assertEqual(entry['task_id'], 'task-001')
        self.assertIn('meta', entry)
        self.assertEqual(entry['meta']['error_type'], 'timeout')

    def test_broadcast_help_creates_jsonl_line(self):
        """Test: broadcast_help should create proper HELP state line"""
        from swarm import status_broadcaster

        sb = status_broadcaster.StatusBroadcaster('worker-1')
        sb.broadcast_help('task-001', 'Need human assistance')

        status_path = os.path.join(sb._ai_swarm_dir, 'status.log')
        with open(status_path) as f:
            line = f.readline().strip()

        entry = json.loads(line)
        self.assertEqual(entry['state'], 'HELP')
        self.assertEqual(entry['task_id'], 'task-001')

    def test_broadcast_skip_creates_jsonl_line(self):
        """Test: broadcast_skip should create proper SKIP state line"""
        from swarm import status_broadcaster

        sb = status_broadcaster.StatusBroadcaster('worker-1')
        sb.broadcast_skip('task-001', 'Skipped by user')

        status_path = os.path.join(sb._ai_swarm_dir, 'status.log')
        with open(status_path) as f:
            line = f.readline().strip()

        entry = json.loads(line)
        self.assertEqual(entry['state'], 'SKIP')
        self.assertEqual(entry['task_id'], 'task-001')

    def test_broadcast_with_message(self):
        """Test: broadcast should include message field when provided"""
        from swarm import status_broadcaster

        sb = status_broadcaster.StatusBroadcaster('worker-1')
        sb.broadcast_start('task-002', 'Custom message here')

        status_path = os.path.join(sb._ai_swarm_dir, 'status.log')
        with open(status_path) as f:
            line = f.readline().strip()

        entry = json.loads(line)
        self.assertEqual(entry['message'], 'Custom message here')

    def test_broadcast_with_meta(self):
        """Test: broadcast should include meta field when provided"""
        from swarm import status_broadcaster

        meta = {'retry_count': 3, 'timeout_sec': 30}
        sb = status_broadcaster.StatusBroadcaster('worker-1')
        sb.broadcast_error('task-003', 'Error', meta=meta)

        status_path = os.path.join(sb._ai_swarm_dir, 'status.log')
        with open(status_path) as f:
            line = f.readline().strip()

        entry = json.loads(line)
        self.assertIn('meta', entry)
        self.assertEqual(entry['meta']['retry_count'], 3)
        self.assertEqual(entry['meta']['timeout_sec'], 30)

    def test_broadcast_timestamp_format(self):
        """Test: ts should be ISO 8601 format with milliseconds"""
        from swarm import status_broadcaster

        sb = status_broadcaster.StatusBroadcaster('worker-1')
        sb.broadcast_start('task-timestamp', 'Testing')

        status_path = os.path.join(sb._ai_swarm_dir, 'status.log')
        with open(status_path) as f:
            line = f.readline().strip()

        entry = json.loads(line)
        ts = entry['ts']

        # Check format: 2026-01-31T12:00:00.000Z
        self.assertRegex(ts, r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$')

    def test_broadcast_creates_directory(self):
        """Test: broadcast should auto-create AI_SWARM_DIR subdirectory"""
        from swarm import status_broadcaster

        # Use AI_SWARM_DIR which is set to a temp dir by fixture
        sb = status_broadcaster.StatusBroadcaster('worker-1')
        sb.broadcast_start('task-dir', 'Testing dir creation')

        # AI_SWARM_DIR should exist
        self.assertTrue(os.path.exists(sb._ai_swarm_dir))
        # status.log should exist
        status_path = os.path.join(sb._ai_swarm_dir, 'status.log')
        self.assertTrue(os.path.exists(status_path))

    def test_broadcast_multiple_lines(self):
        """Test: multiple broadcasts should create multiple JSONL lines"""
        from swarm import status_broadcaster

        sb = status_broadcaster.StatusBroadcaster('worker-1')
        sb.broadcast_start('task-multi', 'Line 1')
        sb.broadcast_done('task-multi', 'Line 2')
        sb.broadcast_error('task-multi', 'Line 3', {'error': True})

        status_path = os.path.join(sb._ai_swarm_dir, 'status.log')
        with open(status_path) as f:
            lines = f.readlines()

        self.assertEqual(len(lines), 3)

        # Parse each line
        for i, line in enumerate(lines):
            entry = json.loads(line.strip())
            self.assertIn('state', entry)
            self.assertIn('task_id', entry)
            self.assertIn('ts', entry)
            self.assertIn('worker_id', entry)

    def test_convenience_methods(self):
        """Test: all convenience methods work correctly"""
        from swarm import status_broadcaster

        sb = status_broadcaster.StatusBroadcaster('worker-1')
        sb.broadcast_start('task-conv', 'start')
        sb.broadcast_done('task-conv', 'done')
        sb.broadcast_wait('task-conv', 'wait')
        sb.broadcast_error('task-conv', 'error')
        sb.broadcast_help('task-conv', 'help')
        sb.broadcast_skip('task-conv', 'skip')

        status_path = os.path.join(sb._ai_swarm_dir, 'status.log')
        with open(status_path) as f:
            lines = f.readlines()

        self.assertEqual(len(lines), 6)

        # Verify each state
        states = ['START', 'DONE', 'WAIT', 'ERROR', 'HELP', 'SKIP']
        for i, (line, expected_state) in enumerate(zip(lines, states)):
            entry = json.loads(line.strip())
            self.assertEqual(entry['state'], expected_state,
                             f"Line {i+1} should be {expected_state}")


if __name__ == '__main__':
    unittest.main(verbosity=2)
