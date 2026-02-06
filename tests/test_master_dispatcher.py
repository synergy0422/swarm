#!/usr/bin/env python3
"""
Unit Tests for Master Dispatcher

Tests for MasterDispatcher class including task loading, worker idle detection,
and dispatch functionality.
"""

import json
import os
import unittest
import tempfile
import shutil
from unittest.mock import MagicMock

from swarm import master_dispatcher
from swarm import master_scanner
from swarm import task_lock
from swarm import status_broadcaster


class TestMasterDispatcher(unittest.TestCase):
    """Test MasterDispatcher functionality"""

    def setUp(self):
        """Create temporary directory for each test"""
        self.test_dir = tempfile.mkdtemp(prefix='dispatcher_test_')
        self.base_dir = os.path.join(self.test_dir, 'ai_swarm')

        # Create directory structure
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, 'locks'), exist_ok=True)

        # Create tasks.json
        self.tasks_file = os.path.join(self.base_dir, 'tasks.json')

        # Set AI_SWARM_DIR for this test directory
        os.environ['AI_SWARM_DIR'] = self.base_dir

        # Initialize dispatcher
        self.dispatcher = master_dispatcher.MasterDispatcher(
            cluster_id='test-cluster'
        )

    def tearDown(self):
        """Clean up temporary directory"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def _create_tasks_file(self, tasks):
        """Helper to create tasks.json with given tasks"""
        tasks_data = {'tasks': tasks}
        with open(self.tasks_file, 'w') as f:
            json.dump(tasks_data, f)

    def test_dispatcher_initialization(self):
        """Test: Dispatcher should initialize with cluster_id"""
        self.assertEqual(self.dispatcher.cluster_id, 'test-cluster')
        self.assertIsInstance(self.dispatcher._scanner, master_scanner.MasterScanner)
        self.assertIsInstance(self.dispatcher._lock_manager, task_lock.TaskLockManager)
        self.assertIsInstance(
            self.dispatcher._broadcaster,
            status_broadcaster.StatusBroadcaster
        )

    def test_load_tasks_from_json(self):
        """Test: load_tasks reads tasks.json with proper format"""
        tasks = [
            {
                'id': 'task-001',
                'prompt': 'Test task 1',
                'priority': 1,
                'status': 'pending'
            },
            {
                'id': 'task-002',
                'prompt': 'Test task 2',
                'priority': 2,
                'status': 'pending'
            }
        ]
        self._create_tasks_file(tasks)

        # Set AI_SWARM_DIR to test directory
        os.environ['AI_SWARM_DIR'] = self.base_dir

        loaded_tasks = self.dispatcher.load_tasks()

        self.assertEqual(len(loaded_tasks), 2)
        self.assertEqual(loaded_tasks[0].task_id, 'task-001')
        self.assertEqual(loaded_tasks[0].command, 'Test task 1')
        self.assertEqual(loaded_tasks[0].priority, 1)
        self.assertEqual(loaded_tasks[0].status, 'pending')

    def test_load_tasks_empty_file(self):
        """Test: load_tasks returns empty list when no tasks.json"""
        os.environ['AI_SWARM_DIR'] = self.base_dir

        loaded_tasks = self.dispatcher.load_tasks()

        self.assertEqual(len(loaded_tasks), 0)
        self.assertIsInstance(loaded_tasks, list)

    def test_is_worker_idle_done_no_lock(self):
        """Test: DONE state with no lock = idle"""
        status = master_scanner.WorkerStatus(
            worker_id='worker-1',
            state='DONE',
            task_id='task-001',
            timestamp='2026-01-31T12:00:00.000Z',
            message='Task completed'
        )

        # Mock scanner to return no lock
        self.dispatcher._scanner.read_lock_state = lambda task_id: None

        is_idle = self.dispatcher.is_worker_idle(status)

        self.assertTrue(is_idle)

    def test_is_worker_idle_error_no_lock(self):
        """Test: ERROR state with no lock = idle"""
        status = master_scanner.WorkerStatus(
            worker_id='worker-1',
            state='ERROR',
            task_id='task-001',
            timestamp='2026-01-31T12:00:00.000Z',
            message='Task failed'
        )

        # Mock scanner to return no lock
        self.dispatcher._scanner.read_lock_state = lambda task_id: None

        is_idle = self.dispatcher.is_worker_idle(status)

        self.assertTrue(is_idle)

    def test_is_worker_idle_skip_no_lock(self):
        """Test: SKIP state with no lock = idle"""
        status = master_scanner.WorkerStatus(
            worker_id='worker-1',
            state='SKIP',
            task_id='task-001',
            timestamp='2026-01-31T12:00:00.000Z',
            message='Task skipped'
        )

        # Mock scanner to return no lock
        self.dispatcher._scanner.read_lock_state = lambda task_id: None

        is_idle = self.dispatcher.is_worker_idle(status)

        self.assertTrue(is_idle)

    def test_is_worker_idle_busy_start(self):
        """Test: START state with task_id = not idle"""
        status = master_scanner.WorkerStatus(
            worker_id='worker-1',
            state='START',
            task_id='task-001',
            timestamp='2026-01-31T12:00:00.000Z',
            message='Starting task'
        )

        is_idle = self.dispatcher.is_worker_idle(status)

        self.assertFalse(is_idle)

    def test_is_worker_idle_start_no_task_id(self):
        """Test: START state with no task_id = idle (waiting for first task)"""
        status = master_scanner.WorkerStatus(
            worker_id='worker-1',
            state='START',
            task_id=None,
            timestamp='2026-01-31T12:00:00.000Z',
            message='Worker started, waiting for task'
        )

        is_idle = self.dispatcher.is_worker_idle(status)

        self.assertTrue(is_idle)

    def test_is_worker_idle_start_empty_task_id(self):
        """Test: START state with empty string task_id = idle (task_id='' in status.log)"""
        status = master_scanner.WorkerStatus(
            worker_id='worker-1',
            state='START',
            task_id='',  # Empty string as seen in status.log
            timestamp='2026-01-31T12:00:00.000Z',
            message='Worker started, waiting for task'
        )

        is_idle = self.dispatcher.is_worker_idle(status)

        self.assertTrue(is_idle)

    def test_is_worker_idle_busy_wait(self):
        """Test: WAIT state = not idle"""
        status = master_scanner.WorkerStatus(
            worker_id='worker-1',
            state='WAIT',
            task_id='task-001',
            timestamp='2026-01-31T12:00:00.000Z',
            message='Waiting for input'
        )

        is_idle = self.dispatcher.is_worker_idle(status)

        self.assertFalse(is_idle)

    def test_is_worker_idle_has_lock(self):
        """Test: worker with DONE but holds lock = not idle"""
        status = master_scanner.WorkerStatus(
            worker_id='worker-1',
            state='DONE',
            task_id='task-001',
            timestamp='2026-01-31T12:00:00.000Z',
            message='Task completed'
        )

        # Create a lock manager to acquire a lock
        lock_mgr = task_lock.TaskLockManager(worker_id='worker-1')
        lock_mgr.acquire_lock('task-001')

        try:
            # Scanner should find the lock
            is_idle = self.dispatcher.is_worker_idle(status)

            self.assertFalse(is_idle)
        finally:
            lock_mgr.release_lock('task-001')

    def test_find_idle_worker(self):
        """Test: find_idle_worker returns first idle worker"""
        worker_statuses = {
            'worker-1': master_scanner.WorkerStatus(
                worker_id='worker-1',
                state='DONE',
                task_id='task-001',
                timestamp='2026-01-31T12:00:00.000Z',
                message='Done'
            ),
            'worker-2': master_scanner.WorkerStatus(
                worker_id='worker-2',
                state='START',
                task_id='task-002',
                timestamp='2026-01-31T12:00:01.000Z',
                message='Starting'
            )
        }

        idle_worker = self.dispatcher.find_idle_worker(worker_statuses)

        self.assertEqual(idle_worker, 'worker-1')

    def test_find_idle_worker_none(self):
        """Test: find_idle_worker returns None when no idle workers"""
        worker_statuses = {
            'worker-1': master_scanner.WorkerStatus(
                worker_id='worker-1',
                state='START',
                task_id='task-001',
                timestamp='2026-01-31T12:00:00.000Z',
                message='Starting'
            ),
            'worker-2': master_scanner.WorkerStatus(
                worker_id='worker-2',
                state='WAIT',
                task_id='task-002',
                timestamp='2026-01-31T12:00:01.000Z',
                message='Waiting'
            )
        }

        idle_worker = self.dispatcher.find_idle_worker(worker_statuses)

        self.assertIsNone(idle_worker)

    def test_dispatch_acquires_lock(self):
        """Test: successful dispatch acquires lock"""
        # Create tasks.json first (required for pre-check)
        tasks = [
            {
                'id': 'task-001',
                'prompt': 'Test command',
                'priority': 1,
                'status': 'pending'
            }
        ]
        self._create_tasks_file(tasks)

        task = master_dispatcher.TaskInfo(
            task_id='task-001',
            command='Test command',
            priority=1,
            status='pending'
        )

        result = self.dispatcher.dispatch_one(task, 'worker-1')

        # Should succeed
        self.assertTrue(result)

        # Lock should be acquired by the target worker
        lock_info = self.dispatcher._scanner.read_lock_state('task-001')
        self.assertIsNotNone(lock_info)
        self.assertEqual(lock_info.worker_id, 'worker-1')

        # Cleanup (use worker's lock manager to release)
        worker_lock_mgr = task_lock.TaskLockManager(worker_id='worker-1')
        worker_lock_mgr.release_lock('task-001')

    def test_dispatch_skips_locked_task(self):
        """Test: dispatch skips task with valid lock"""
        task = master_dispatcher.TaskInfo(
            task_id='task-001',
            command='Test command',
            priority=1,
            status='pending'
        )

        # Another worker acquires the lock
        other_lock_mgr = task_lock.TaskLockManager(worker_id='worker-2')
        other_lock_mgr.acquire_lock('task-001')

        try:
            # Try to dispatch
            result = self.dispatcher.dispatch_one(task, 'worker-1')

            # Should fail
            self.assertFalse(result)
        finally:
            other_lock_mgr.release_lock('task-001')

    def test_dispatch_to_idle_worker(self):
        """Test: dispatch_all dispatches to idle worker"""
        # Create tasks
        tasks = [
            {
                'id': 'task-001',
                'prompt': 'Test task 1',
                'priority': 1,
                'status': 'pending'
            }
        ]
        self._create_tasks_file(tasks)
        os.environ['AI_SWARM_DIR'] = self.base_dir

        # Create worker status
        worker_statuses = {
            'worker-1': master_scanner.WorkerStatus(
                worker_id='worker-1',
                state='DONE',
                task_id=None,
                timestamp='2026-01-31T12:00:00.000Z',
                message='Idle'
            )
        }

        results = self.dispatcher.dispatch_all(worker_statuses)

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].success)
        self.assertEqual(results[0].task_id, 'task-001')
        self.assertEqual(results[0].worker_id, 'worker-1')

        # Cleanup
        self.dispatcher._lock_manager.release_lock('task-001')

    def test_dispatch_result_structure(self):
        """Test: DispatchResult has correct fields"""
        result = master_dispatcher.DispatchResult(
            success=True,
            task_id='task-001',
            worker_id='worker-1',
            reason=None
        )

        self.assertTrue(result.success)
        self.assertEqual(result.task_id, 'task-001')
        self.assertEqual(result.worker_id, 'worker-1')
        self.assertIsNone(result.reason)

    def test_task_info_structure(self):
        """Test: TaskInfo has correct fields"""
        task = master_dispatcher.TaskInfo(
            task_id='task-001',
            command='python run.py',
            priority=1,
            status='pending'
        )

        self.assertEqual(task.task_id, 'task-001')
        self.assertEqual(task.command, 'python run.py')
        self.assertEqual(task.priority, 1)
        self.assertEqual(task.status, 'pending')

    def test_create_dispatcher_factory(self):
        """Test: create_dispatcher factory function works"""
        dispatcher = master_dispatcher.create_dispatcher('test-cluster-2')

        self.assertIsInstance(dispatcher, master_dispatcher.MasterDispatcher)
        self.assertEqual(dispatcher.cluster_id, 'test-cluster-2')

    def test_dispatch_one_broadcasts_assigned_state(self):
        """Test: dispatch_one() broadcasts ASSIGNED state (not START)"""
        from unittest.mock import MagicMock, patch

        # Create task first (required for pre-check)
        tasks = [
            {
                'id': 'task-test-001',
                'prompt': 'Test command',
                'priority': 1,
                'status': 'pending'
            }
        ]
        self._create_tasks_file(tasks)

        # Create task first
        task = master_dispatcher.TaskInfo(
            task_id='task-test-001',
            command='Test command',
            priority=1,
            status='pending'
        )

        # Set AI_SWARM_DIR to temp directory for isolation (restored in tearDown)
        original_ai_swarm_dir = os.environ.get('AI_SWARM_DIR')
        os.environ['AI_SWARM_DIR'] = self.base_dir
        try:
            # Create a new dispatcher for this specific test
            dispatcher = master_dispatcher.MasterDispatcher(cluster_id='test-cluster')

            # Create a mock broadcaster and replace _broadcaster
            mock_broadcaster = MagicMock()
            dispatcher._broadcaster = mock_broadcaster

            # Dispatch the task
            result = dispatcher.dispatch_one(task, 'worker-1')

            # Verify dispatch returned success
            self.assertTrue(result)

            # Verify _broadcast was called
            mock_broadcaster._broadcast.assert_called_once()

            # Get the call arguments
            call_kwargs = mock_broadcaster._broadcast.call_args.kwargs

            # Verify ASSIGNED state was broadcast (not START)
            self.assertEqual(
                call_kwargs['state'],
                status_broadcaster.BroadcastState.ASSIGNED,
                "dispatch_one() should broadcast ASSIGNED state, not START"
            )

            # Verify task_id is correct
            self.assertEqual(call_kwargs['task_id'], 'task-test-001')

            # Verify message mentions assignment
            self.assertIn('worker-1', call_kwargs['message'])

            # Verify assigned_worker_id is in meta
            self.assertIn('assigned_worker_id', call_kwargs['meta'])
            self.assertEqual(call_kwargs['meta']['assigned_worker_id'], 'worker-1')

            # Verify old 'event' key is NOT present in meta
            self.assertNotIn('event', call_kwargs['meta'])

            # Cleanup using worker's lock manager
            worker_lock_mgr = task_lock.TaskLockManager(worker_id='worker-1')
            worker_lock_mgr.release_lock('task-test-001')
        finally:
            # Restore original AI_SWARM_DIR
            if original_ai_swarm_dir is None:
                os.environ.pop('AI_SWARM_DIR', None)
            else:
                os.environ['AI_SWARM_DIR'] = original_ai_swarm_dir

    def test_no_duplicate_dispatch_same_task(self):
        """
        Test: 同一任务不会被派发到多个 Worker

        场景:
        1. 创建 1 个 pending 任务
        2. 创建 2 个 idle workers
        3. 多次调用 dispatch_all
        4. 验证只有 1 个 Worker 收到任务
        """
        # Setup
        os.environ['AI_SWARM_DIR'] = self.base_dir

        # 创建 tasks.json: 1 个 pending 任务
        tasks = [
            {
                'id': 'task-001',
                'prompt': 'Test task',
                'priority': 1,
                'status': 'pending'
            }
        ]
        self._create_tasks_file(tasks)

        # 创建 2 个 idle workers
        worker_statuses = {
            'worker-1': master_scanner.WorkerStatus(
                worker_id='worker-1',
                state='DONE',
                task_id=None,
                timestamp='2026-01-31T12:00:00.000Z',
                message='Idle'
            ),
            'worker-2': master_scanner.WorkerStatus(
                worker_id='worker-2',
                state='DONE',
                task_id=None,
                timestamp='2026-01-31T12:00:00.000Z',
                message='Idle'
            )
        }

        # 多次 dispatch_all 模拟并发
        results1 = self.dispatcher.dispatch_all(worker_statuses)
        results2 = self.dispatcher.dispatch_all(worker_statuses)
        results3 = self.dispatcher.dispatch_all(worker_statuses)

        # 验证: 总共只有 1 次成功派发
        total_success = len([r for r in results1 + results2 + results3 if r.success])
        self.assertEqual(
            total_success, 1,
            f"同一任务不应派发到多个 Worker，实际派发次数: {total_success}"
        )

        # 验证: tasks.json 状态为 ASSIGNED
        updated_tasks = self.dispatcher.load_tasks()
        self.assertEqual(updated_tasks[0].status, 'ASSIGNED')

        # Cleanup
        worker_lock_mgr = task_lock.TaskLockManager(worker_id='worker-1')
        worker_lock_mgr.release_lock('task-001')
        worker_lock_mgr = task_lock.TaskLockManager(worker_id='worker-2')
        worker_lock_mgr.release_lock('task-001')

    def test_dispatch_fails_if_task_already_assigned(self):
        """
        Test: 如果任务已被分配，后续派发应失败

        场景:
        1. 创建 tasks.json，task-A 状态为 ASSIGNED
        2. 尝试派发 task-A
        3. 验证派发失败
        """
        # Setup
        os.environ['AI_SWARM_DIR'] = self.base_dir

        # 创建 tasks.json: 任务已被 ASSIGNED
        tasks = [
            {
                'id': 'task-001',
                'prompt': 'Test task',
                'priority': 1,
                'status': 'ASSIGNED',
                'assigned_worker_id': 'worker-1'
            }
        ]
        self._create_tasks_file(tasks)

        # 尝试派发 (传入的 TaskInfo 状态是 pending，但实际 tasks.json 是 ASSIGNED)
        task = master_dispatcher.TaskInfo(
            task_id='task-001',
            command='Test command',
            priority=1,
            status='pending'
        )
        result = self.dispatcher.dispatch_one(task, 'worker-2')

        # 验证: 派发失败
        self.assertFalse(result, "任务已 ASSIGNED 时不应再次派发")

    def test_atomic_status_update(self):
        """
        Test: _update_task_status 原子更新并返回 bool

        场景:
        1. 调用 _update_task_status
        2. 验证返回 True
        3. 验证 tasks.json 状态正确更新
        """
        # Setup
        os.environ['AI_SWARM_DIR'] = self.base_dir

        tasks = [
            {
                'id': 'task-001',
                'prompt': 'Test task',
                'priority': 1,
                'status': 'pending'
            }
        ]
        self._create_tasks_file(tasks)

        # 调用
        result = self.dispatcher._update_task_status(
            task_id='task-001',
            worker_id='worker-1',
            ts_ms=1730000000000
        )

        # 验证: 返回 True
        self.assertTrue(result, "_update_task_status 应返回 True")

        # 验证: 状态更新 (TaskInfo 没有 assigned_worker_id，检查 tasks.json)
        with open(self.tasks_file, 'r') as f:
            data = json.load(f)
        task_dict = data['tasks'][0]
        self.assertEqual(task_dict['status'], 'ASSIGNED')
        self.assertEqual(task_dict['assigned_worker_id'], 'worker-1')

    def test_atomic_status_update_nonexistent_task(self):
        """
        Test: _update_task_status 处理不存在的任务

        场景:
        1. 调用 _update_task_status 更新不存在的任务
        2. 验证返回 False
        """
        # Setup
        os.environ['AI_SWARM_DIR'] = self.base_dir

        tasks = [
            {
                'id': 'task-001',
                'prompt': 'Test task',
                'priority': 1,
                'status': 'pending'
            }
        ]
        self._create_tasks_file(tasks)

        # 调用 (不存在的任务)
        result = self.dispatcher._update_task_status(
            task_id='task-nonexistent',
            worker_id='worker-1',
            ts_ms=1730000000000
        )

        # 验证: 返回 False
        self.assertFalse(result, "_update_task_status 对不存在的任务应返回 False")

    def test_dispatch_one_rollback_on_status_update_failure(self):
        """
        Test: 状态更新失败时释放锁

        场景:
        1. 模拟 _update_task_status 失败
        2. 验证锁被释放
        3. 验证派发返回 False
        """
        # Setup
        os.environ['AI_SWARM_DIR'] = self.base_dir

        # 创建 tasks.json
        tasks = [
            {
                'id': 'task-001',
                'prompt': 'Test task',
                'priority': 1,
                'status': 'pending'
            }
        ]
        self._create_tasks_file(tasks)

        # Mock _update_task_status 使其失败
        original_update = self.dispatcher._update_task_status
        self.dispatcher._update_task_status = lambda *args, **kwargs: False

        try:
            task = master_dispatcher.TaskInfo(
                task_id='task-001',
                command='Test command',
                priority=1,
                status='pending'
            )
            result = self.dispatcher.dispatch_one(task, 'worker-1')

            # 验证: 派发失败
            self.assertFalse(result, "状态更新失败时应返回 False")

            # 验证: 锁被释放 (另一个 worker 可以获取)
            other_lock_mgr = task_lock.TaskLockManager(worker_id='worker-2')
            acquired = other_lock_mgr.acquire_lock('task-001')
            self.assertTrue(acquired, "状态更新失败后锁应被释放")

            # Cleanup
            other_lock_mgr.release_lock('task-001')
        finally:
            # Restore original method
            self.dispatcher._update_task_status = original_update


if __name__ == '__main__':
    unittest.main(verbosity=2)
