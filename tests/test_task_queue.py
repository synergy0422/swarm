#!/usr/bin/env python3
"""
Test suite for task_queue.py
TDD Phase 2: Task Queue System
"""

import os
import sys
import json
import tempfile
import shutil
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config


class TestTaskQueue(unittest.TestCase):
    """Test suite for task queue manager"""

    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp(prefix='task_queue_test_')
        self.tasks_file = os.path.join(self.test_dir, 'tasks.json')

        # Sample tasks
        self.sample_tasks = {
            "tasks": [
                {
                    "id": "task_001",
                    "prompt": "Test task 1",
                    "status": "pending",
                    "priority": 1
                },
                {
                    "id": "task_002",
                    "prompt": "Test task 2",
                    "system": "Senior Python Architect",
                    "max_tokens": 2048,
                    "model": "claude-3-sonnet-20240229",
                    "status": "pending",
                    "priority": 2
                }
            ]
        }

    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_create_new_queue_file(self):
        """Test: Should create new tasks.json if it doesn't exist"""
        # This will FAIL until task_queue.py is implemented
        import task_queue

        tq = task_queue.TaskQueue(self.tasks_file)
        tq.init_queue()

        self.assertTrue(os.path.exists(self.tasks_file))

        with open(self.tasks_file, 'r') as f:
            data = json.load(f)

        self.assertIn('tasks', data)
        self.assertEqual(data['tasks'], [])

    def test_load_existing_queue(self):
        """Test: Should load existing tasks from file"""
        # Create initial tasks file
        with open(self.tasks_file, 'w') as f:
            json.dump(self.sample_tasks, f)

        import task_queue

        tq = task_queue.TaskQueue(self.tasks_file)
        tasks = tq.load_tasks()

        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0]['id'], 'task_001')

    def test_get_pending_tasks(self):
        """Test: Should return only pending tasks"""
        with open(self.tasks_file, 'w') as f:
            json.dump(self.sample_tasks, f)

        import task_queue

        tq = task_queue.TaskQueue(self.tasks_file)
        pending = tq.get_pending_tasks()

        self.assertEqual(len(pending), 2)
        self.assertEqual(pending[0]['status'], 'pending')

    def test_assign_task_to_worker(self):
        """Test: Should assign task to worker and update status"""
        with open(self.tasks_file, 'w') as f:
            json.dump(self.sample_tasks, f)

        import task_queue

        tq = task_queue.TaskQueue(self.tasks_file)
        tq.assign_task('task_001', 'worker-1')

        tasks = tq.load_tasks()
        task = [t for t in tasks if t['id'] == 'task_001'][0]

        self.assertEqual(task['assigned_to'], 'worker-1')
        self.assertEqual(task['status'], 'assigned')

    def test_complete_task(self):
        """Test: Should mark task as completed with result file"""
        with open(self.tasks_file, 'w') as f:
            json.dump(self.sample_tasks, f)

        import task_queue

        tq = task_queue.TaskQueue(self.tasks_file)
        tq.complete_task('task_001', '/tmp/ai_swarm/results/task_001.md')

        tasks = tq.load_tasks()
        task = [t for t in tasks if t['id'] == 'task_001'][0]

        self.assertEqual(task['status'], 'completed')
        self.assertEqual(task['result_file'], '/tmp/ai_swarm/results/task_001.md')

    def test_fail_task(self):
        """Test: Should mark task as failed with error message"""
        with open(self.tasks_file, 'w') as f:
            json.dump(self.sample_tasks, f)

        import task_queue

        tq = task_queue.TaskQueue(self.tasks_file)
        tq.fail_task('task_001', 'API timeout')

        tasks = tq.load_tasks()
        task = [t for t in tasks if t['id'] == 'task_001'][0]

        self.assertEqual(task['status'], 'failed')
        self.assertEqual(task['error'], 'API timeout')

    def test_add_new_task(self):
        """Test: Should add new task to queue"""
        with open(self.tasks_file, 'w') as f:
            json.dump(self.sample_tasks, f)

        import task_queue

        tq = task_queue.TaskQueue(self.tasks_file)
        tq.add_task("New task prompt", priority=3)

        tasks = tq.load_tasks()

        self.assertEqual(len(tasks), 3)
        self.assertEqual(tasks[2]['prompt'], 'New task prompt')
        self.assertEqual(tasks[2]['status'], 'pending')

    def test_validate_valid_task(self):
        """Test: Should accept valid task"""
        import task_queue

        valid_task = {
            "id": "task_003",
            "prompt": "Valid prompt",
            "system": "Test persona",
            "max_tokens": 1024,
            "model": "claude-3-haiku-20240307"
        }

        error = task_queue.validate_task(valid_task)

        self.assertIsNone(error)

    def test_validate_missing_required_fields(self):
        """Test: Should reject task without required fields"""
        import task_queue

        invalid_task = {
            "system": "Test persona"
            # Missing required 'id' and 'prompt'
        }

        error = task_queue.validate_task(invalid_task)

        self.assertIsNotNone(error)

    def test_validate_invalid_model(self):
        """Test: Should reject task with invalid model"""
        import task_queue

        invalid_task = {
            "id": "task_004",
            "prompt": "Test",
            "model": "invalid-model-name"
        }

        error = task_queue.validate_task(invalid_task)

        self.assertIsNotNone(error)
        self.assertIn('model', error.lower())


if __name__ == '__main__':
    unittest.main(verbosity=2)
