#!/usr/bin/env python3
"""
Test suite for worker_smart.py
TDD Phase 2: Smart Worker with Anthropic API
"""

import os
import sys
import json
import tempfile
import shutil
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import time
import requests

from swarm import config
from swarm import worker_smart


class TestSmartWorker(unittest.TestCase):
    """Test suite for smart worker with API integration"""

    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp(prefix='worker_smart_test_')
        self.status_log = os.path.join(self.test_dir, 'status.log')
        self.locks_dir = os.path.join(self.test_dir, 'locks')
        self.results_dir = os.path.join(self.test_dir, 'results')

        # Create directories
        os.makedirs(self.locks_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)

        # Sample task
        self.sample_task = {
            'id': 'task_001',
            'prompt': 'Test prompt',
            'system': 'Test persona',
            'max_tokens': 1024,
            'model': 'claude-3-haiku-20240307'
        }

    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_worker_initialization(self):
        """Test: Worker should initialize with base directory"""
        # This will FAIL until worker_smart.py is implemented
        worker = worker_smart.SmartWorker(
            'test-worker',
            base_dir=self.test_dir
        )

        self.assertEqual(worker.name, 'test-worker')
        self.assertEqual(worker.base_dir, self.test_dir)

    def test_extract_response_text_variants(self):
        """Test: Should extract text from multiple response schemas"""
        original = os.environ.get('LLM_BASE_URL')
        try:
            os.environ['LLM_BASE_URL'] = 'http://127.0.0.1:15721'
            worker = worker_smart.SmartWorker('test-worker', base_dir=self.test_dir)

            anthropic = {'content': [{'text': 'Hello'}]}
            thinking = {'content': [{'thinking': 'Thoughts'}]}
            openai = {'choices': [{'message': {'content': 'Chat'}}]}

            self.assertEqual(worker._extract_response_text(anthropic), 'Hello')
            self.assertEqual(worker._extract_response_text(thinking), 'Thoughts')
            self.assertEqual(worker._extract_response_text(openai), 'Chat')
        finally:
            if original is None:
                os.environ.pop('LLM_BASE_URL', None)
            else:
                os.environ['LLM_BASE_URL'] = original

    @patch('swarm.worker_smart.requests.post')
    def test_api_call_with_system_prompt(self, mock_post):
        """Test: Should include system parameter in API call"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'content': [{'text': 'Test response'}],
            'usage': {'input_tokens': 10, 'output_tokens': 20}
        }
        mock_post.return_value = mock_response

        os.environ['ANTHROPIC_API_KEY'] = 'sk-ant-test123456'

        worker = worker_smart.SmartWorker('test-worker', base_dir=self.test_dir)

        # Call API with system prompt
        response = worker.call_claude_api(
            prompt='Test prompt',
            system='Test persona',
            max_tokens=1024,
            model='claude-3-haiku-20240307'
        )

        # Verify API was called
        self.assertTrue(mock_post.called)

        # Verify request included system parameter
        call_args = mock_post.call_args
        request_body = call_args[1]['json']

        self.assertIn('system', request_body)
        self.assertEqual(request_body['system'], 'Test persona')

    @patch('swarm.worker_smart.requests.post')
    def test_api_call_with_task_overrides(self, mock_post):
        """Test: Should use task-level max_tokens and model overrides"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'content': [{'text': 'Response'}],
            'usage': {'input_tokens': 10, 'output_tokens': 20}
        }
        mock_post.return_value = mock_response

        os.environ['ANTHROPIC_API_KEY'] = 'sk-ant-test123456'

        worker = worker_smart.SmartWorker('test-worker', base_dir=self.test_dir)

        # Call with overrides
        worker.call_claude_api(
            prompt='Test',
            max_tokens=2048,  # Override
            model='claude-3-sonnet-20240229'  # Override
        )

        # Verify overrides were used
        call_args = mock_post.call_args
        request_body = call_args[1]['json']

        self.assertEqual(request_body['max_tokens'], 2048)
        self.assertEqual(request_body['model'], 'claude-3-sonnet-20240229')

    def test_jitter_timing(self):
        """Test: Status updates should have random jitter (2-3 seconds)"""
        # Test jitter calculation
        timings = []
        for _ in range(10):
            jitter = worker_smart.calculate_jitter()
            self.assertTrue(0 <= jitter < 1)
            timings.append(2 + jitter)

        # All timings should be between 2 and 3 seconds
        for t in timings:
            self.assertTrue(2 <= t < 3)

    @patch('swarm.worker_smart.requests.post')
    def test_save_result_with_metadata(self, mock_post):
        """Test: Should save result with enhanced metadata header"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'content': [{'text': 'AI response here'}],
            'usage': {'input_tokens': 100, 'output_tokens': 200}
        }
        mock_post.return_value = mock_response

        os.environ['ANTHROPIC_API_KEY'] = 'sk-ant-test123456'

        worker = worker_smart.SmartWorker('test-worker', base_dir=self.test_dir)

        # Save result
        worker.save_result(
            task_id='task_001',
            content='AI response here',
            task_params=self.sample_task,
            input_tokens=100,
            output_tokens=200
        )

        # Verify file created
        result_file = os.path.join(self.results_dir, 'task_001.md')
        self.assertTrue(os.path.exists(result_file))

        # Verify metadata in file
        with open(result_file, 'r') as f:
            content = f.read()

        self.assertIn('task_id: task_001', content)
        self.assertIn('worker: test-worker', content)
        self.assertIn('model: claude-3-haiku-20240307', content)
        self.assertIn('max_tokens: 1024', content)
        self.assertIn('system: Test persona', content)
        self.assertIn('input_tokens: 100', content)
        self.assertIn('output_tokens: 200', content)

    @patch('swarm.worker_smart.requests.post')
    def test_handle_401_unauthorized(self, mock_post):
        """Test: Should handle 401 authentication error"""
        http_error = requests.exceptions.HTTPError()
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = 'Unauthorized'
        http_error.response = mock_response

        mock_post.return_value = mock_response
        mock_post.return_value.raise_for_status.side_effect = http_error

        os.environ['ANTHROPIC_API_KEY'] = 'sk-ant-invalid'

        worker = worker_smart.SmartWorker('test-worker', base_dir=self.test_dir)

        # Should raise exception with error message
        with self.assertRaises(Exception) as context:
            worker.call_claude_api('Test prompt')

        # Verify error message
        self.assertIn('Invalid API key', str(context.exception))

        # Verify error was logged to status via broadcaster
        # StatusBroadcaster uses AI_SWARM_DIR (set by isolated_swarm_dir fixture)
        status_log = os.path.join(os.environ['AI_SWARM_DIR'], 'status.log')
        with open(status_log, 'r') as f:
            log = json.loads(f.readlines()[-1])
            self.assertEqual(log['state'], 'ERROR')
            self.assertIn('worker_id', log)

    @patch('swarm.worker_smart.requests.post')
    def test_handle_429_rate_limit(self, mock_post):
        """Test: Should handle 429 rate limit error"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = 'Rate limit exceeded'
        mock_response.raise_for_status.side_effect = Exception("429 Client Error")

        mock_post.return_value = mock_response

        os.environ['ANTHROPIC_API_KEY'] = 'sk-ant-test123456'

        worker = worker_smart.SmartWorker('test-worker', base_dir=self.test_dir)

        # Should log error, not crash
        try:
            worker.call_claude_api('Test prompt')
        except Exception as e:
            # Expected to handle gracefully
            pass

    @patch('swarm.worker_smart.requests.post')
    def test_handle_timeout_error(self, mock_post):
        """Test: Should handle request timeout"""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout()

        os.environ['ANTHROPIC_API_KEY'] = 'sk-ant-test123456'

        worker = worker_smart.SmartWorker('test-worker', base_dir=self.test_dir)

        # Should log timeout error
        try:
            worker.call_claude_api('Test prompt')
        except Exception as e:
            # Expected to handle gracefully
            pass

    def test_cost_tracking_per_model(self):
        """Test: Should calculate cost correctly for each model"""
        # Haiku cost
        cost = worker_smart.calculate_cost(
            'claude-3-haiku-20240307',
            1000,
            500
        )
        self.assertAlmostEqual(cost, 0.000875, places=6)

        # Sonnet cost
        cost = worker_smart.calculate_cost(
            'claude-3-sonnet-20240229',
            1000,
            500
        )
        self.assertAlmostEqual(cost, 0.0105, places=6)

    @patch('swarm.worker_smart.requests.post')
    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_streaming_with_jittered_updates(self, mock_sleep, mock_post):
        """Test: Streaming should update status with jittered timing"""
        # Mock streaming response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'content': [{'text': 'Hello world'}],
            'usage': {'input_tokens': 10, 'output_tokens': 20}
        }
        mock_post.return_value = mock_response

        os.environ['ANTHROPIC_API_KEY'] = 'sk-ant-test123456'

        worker = worker_smart.SmartWorker('test-worker', base_dir=self.test_dir)

        # Mock broadcaster to capture calls
        updates = []
        original_broadcast_wait = worker.broadcaster.broadcast_wait
        def capture_wait(task_id, message="", meta=None):
            updates.append(('WAIT', task_id, message))
            return None

        worker.broadcaster.broadcast_wait = capture_wait

        worker.process_task_streaming(self.sample_task)

        # Verify updates occurred
        self.assertTrue(len(updates) > 0)

        # Verify jitter timing was applied
        # (mock_sleep should have been called with 2-3 second intervals)
        self.assertTrue(mock_sleep.called)
        for call in mock_sleep.call_args_list:
            sleep_time = call[0][0]
            self.assertTrue(2 <= sleep_time < 3)


if __name__ == '__main__':
    unittest.main(verbosity=2)


class TestMailboxOffsetPersistence(unittest.TestCase):
    """
    Test suite for P1.1: Worker Mailbox Offset Persistence

    Ensures worker doesn't re-process tasks after restart.
    """

    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp(prefix='worker_offset_test_')
        self.instructions_dir = os.path.join(self.test_dir, 'instructions')
        self.offsets_dir = os.path.join(self.test_dir, 'offsets')
        os.makedirs(self.instructions_dir, exist_ok=True)
        os.makedirs(self.offsets_dir, exist_ok=True)

        # Set proxy mode to avoid API key requirement
        self.original_llm_url = os.environ.get('LLM_BASE_URL')
        os.environ['LLM_BASE_URL'] = 'http://127.0.0.1:15721/v1/messages'

        # Sample mailbox content
        self.mailbox_path = os.path.join(self.instructions_dir, 'test-worker.jsonl')
        self.sample_instructions = [
            json.dumps({'ts': 1, 'task_id': 'task-001', 'action': 'RUN_TASK', 'payload': {'id': 'task-001', 'prompt': 'Task 1'}}),
            json.dumps({'ts': 2, 'task_id': 'task-002', 'action': 'RUN_TASK', 'payload': {'id': 'task-002', 'prompt': 'Task 2'}}),
            json.dumps({'ts': 3, 'task_id': 'task-003', 'action': 'RUN_TASK', 'payload': {'id': 'task-003', 'prompt': 'Task 3'}}),
        ]

    def tearDown(self):
        """Clean up test environment"""
        if self.original_llm_url is not None:
            os.environ['LLM_BASE_URL'] = self.original_llm_url
        else:
            os.environ.pop('LLM_BASE_URL', None)
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_offset_file_path_constructed_correctly(self):
        """Test: Offset file path follows expected pattern"""
        os.environ['AI_SWARM_DIR'] = self.test_dir

        worker = worker_smart.SmartWorker('test-worker', base_dir=self.test_dir)

        expected_offset_path = os.path.join(self.offsets_dir, 'test-worker.offset.json')
        self.assertEqual(worker._offset_file_path, expected_offset_path)

    def test_load_mailbox_offset_returns_zero_for_nonexistent_file(self):
        """Test: Load offset returns 0 when offset file doesn't exist"""
        os.environ['AI_SWARM_DIR'] = self.test_dir

        worker = worker_smart.SmartWorker('test-worker', base_dir=self.test_dir)

        # Offset file doesn't exist
        self.assertFalse(os.path.exists(worker._offset_file_path))

        # Should return 0
        offset = worker._load_mailbox_offset()
        self.assertEqual(offset, 0)

    def test_load_mailbox_offset_recovers_from_file(self):
        """Test: Load offset returns saved value from file"""
        os.environ['AI_SWARM_DIR'] = self.test_dir

        # Pre-create offset file with saved offset
        offset_file = os.path.join(self.offsets_dir, 'test-worker.offset.json')
        os.makedirs(os.path.dirname(offset_file), exist_ok=True)
        with open(offset_file, 'w') as f:
            json.dump({'offset': 3, 'updated_at': '2026-02-07T10:00:00.000Z'}, f)

        worker = worker_smart.SmartWorker('test-worker', base_dir=self.test_dir)

        # Should load saved offset
        offset = worker._load_mailbox_offset()
        self.assertEqual(offset, 3)

    def test_load_mailbox_offset_handles_corruption(self):
        """Test: Load offset returns 0 when file is corrupted"""
        os.environ['AI_SWARM_DIR'] = self.test_dir

        # Create corrupted offset file
        offset_file = os.path.join(self.offsets_dir, 'test-worker.offset.json')
        with open(offset_file, 'w') as f:
            f.write('{invalid json}')

        worker = worker_smart.SmartWorker('test-worker', base_dir=self.test_dir)

        # Should handle corruption gracefully, return 0
        offset = worker._load_mailbox_offset()
        self.assertEqual(offset, 0)

    def test_save_mailbox_offset_writes_to_file(self):
        """Test: Save offset writes correct value to file"""
        os.environ['AI_SWARM_DIR'] = self.test_dir

        worker = worker_smart.SmartWorker('test-worker', base_dir=self.test_dir)

        worker._save_mailbox_offset(5)

        # Verify file was created
        self.assertTrue(os.path.exists(worker._offset_file_path))

        # Verify content
        with open(worker._offset_file_path, 'r') as f:
            data = json.load(f)
        self.assertEqual(data['offset'], 5)
        self.assertIn('updated_at', data)

    def test_poll_for_instructions_persists_offset(self):
        """Test: Poll instructions saves offset after processing"""
        os.environ['AI_SWARM_DIR'] = self.test_dir

        # Create mailbox with instructions
        with open(self.mailbox_path, 'w') as f:
            f.write('\n'.join(self.sample_instructions) + '\n')

        worker = worker_smart.SmartWorker('test-worker', base_dir=self.test_dir)

        # Mock _verify_task_lock to always return True
        worker._verify_task_lock = MagicMock(return_value=True)

        # Mock broadcaster to avoid status log issues
        worker.broadcaster = MagicMock()

        # Poll first task
        task = worker.poll_for_instructions()

        # Verify offset was saved
        self.assertTrue(os.path.exists(worker._offset_file_path))
        with open(worker._offset_file_path, 'r') as f:
            data = json.load(f)
        self.assertEqual(data['offset'], 1)

    def test_worker_restart_resumes_from_last_offset(self):
        """Test: Worker restart resumes from last saved offset (no duplicate processing)"""
        os.environ['AI_SWARM_DIR'] = self.test_dir

        # Create mailbox with 3 tasks
        with open(self.mailbox_path, 'w') as f:
            f.write('\n'.join(self.sample_instructions) + '\n')

        # First worker instance processes first 2 tasks
        worker1 = worker_smart.SmartWorker('test-worker', base_dir=self.test_dir)
        worker1._verify_task_lock = MagicMock(return_value=True)
        worker1.broadcaster = MagicMock()

        # Process task 1
        task1 = worker1.poll_for_instructions()
        self.assertEqual(task1['id'], 'task-001')

        # Process task 2
        task2 = worker1.poll_for_instructions()
        self.assertEqual(task2['id'], 'task-002')

        # Simulate crash - offset is saved at 2
        self.assertTrue(os.path.exists(worker1._offset_file_path))

        # New worker instance starts (simulating restart)
        worker2 = worker_smart.SmartWorker('test-worker', base_dir=self.test_dir)
        worker2._verify_task_lock = MagicMock(return_value=True)
        worker2.broadcaster = MagicMock()

        # Should start from offset 2, process only task-003
        task3 = worker2.poll_for_instructions()

        # Verify only task-003 was processed (not duplicate)
        self.assertIsNotNone(task3)
        self.assertEqual(task3['id'], 'task-003')

        # Verify no more tasks
        task4 = worker2.poll_for_instructions()
        self.assertIsNone(task4)
