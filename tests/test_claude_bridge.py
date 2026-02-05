#!/usr/bin/env python3
"""
Unit tests for claude_bridge.py
"""

import pytest
import tempfile
import os
import json
from unittest.mock import patch, MagicMock

from swarm.claude_bridge import TaskParser, DedupeState, ClaudeBridge, LineFilter


class TestTaskParser:
    """TaskParser unit tests"""

    def setup_method(self):
        self.parser = TaskParser()

    def test_parse_task_prefix(self):
        """Test /task prefix parsing"""
        assert self.parser.parse("/task Review PR #123") == "Review PR #123"
        assert self.parser.parse("/task  Fix bug in login  ") == "Fix bug in login"
        assert self.parser.parse("  /task Task with spaces") == "Task with spaces"

    def test_parse_task_colon(self):
        """Test TASK: prefix parsing"""
        assert self.parser.parse("TASK: Fix bug") == "Fix bug"
        assert self.parser.parse("TASK:  Update docs  ") == "Update docs"
        assert self.parser.parse("  TASK: Indented task") == "Indented task"

    def test_parse_ignores_non_task(self):
        """Test ignoring non-task lines"""
        # Claude echo (not matching)
        assert self.parser.parse("Sure, I will help you") is None
        assert self.parser.parse("Here's what I found:") is None
        assert self.parser.parse("task: lowercase (not matching)") is None
        assert self.parser.parse("/task_without_space") is None
        assert self.parser.parse("/task") is None  # No prompt

    def test_parse_empty(self):
        """Test empty lines"""
        assert self.parser.parse("") is None
        assert self.parser.parse("   ") is None

    def test_parse_complex_prompt(self):
        """Test complex task prompts"""
        prompt = "Review PR #123 and leave comments on the authentication module"
        assert self.parser.parse(f"/task {prompt}") == prompt

        prompt2 = "Fix authentication bug in login module with detailed error logging"
        assert self.parser.parse(f"TASK: {prompt2}") == prompt2


class TestDedupeState:
    """DedupeState unit tests"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = os.path.join(self.temp_dir, "dedupe.json")
        self.dedupe = DedupeState(self.state_file)

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_new_task_not_duplicate(self):
        """Test new task is not duplicate"""
        is_dup, hash_id = self.dedupe.is_duplicate("Task A")
        assert is_dup is False
        assert hash_id is not None
        assert len(hash_id) == 16  # MD5 hexdigest[:16]

    def test_duplicate_detected(self):
        """Test duplicate detection"""
        task = "Same task"
        is_dup, hash_id = self.dedupe.is_duplicate(task)
        assert is_dup is False

        # Mark as seen
        self.dedupe.mark_seen(hash_id)

        # Should now be duplicate
        is_dup2, _ = self.dedupe.is_duplicate(task)
        assert is_dup2 is True

    def test_different_tasks_not_duplicate(self):
        """Test different tasks are not duplicates"""
        hash1 = self.dedupe.is_duplicate("Task A")[1]
        hash2 = self.dedupe.is_duplicate("Task B")[1]

        assert hash1 != hash2
        assert self.dedupe.is_duplicate("Task A") == (False, hash1)
        assert self.dedupe.is_duplicate("Task B") == (False, hash2)

    def test_persistence(self):
        """Test state persistence"""
        task = "Persistent task"
        is_dup, hash_id = self.dedupe.is_duplicate(task)
        assert is_dup is False

        self.dedupe.mark_seen(hash_id)

        # Create new instance (simulating restart)
        new_dedupe = DedupeState(self.state_file)
        is_dup2, _ = new_dedupe.is_duplicate(task)
        assert is_dup2 is True

    def test_cache_limit(self):
        """Test cache size limit"""
        # Create dedupe with small cache size
        small_cache_dedupe = DedupeState(self.state_file, cache_size=10)

        # Add more than cache_size tasks
        for i in range(20):
            _, hash_id = small_cache_dedupe.is_duplicate(f"Task {i}")
            small_cache_dedupe.mark_seen(hash_id)

        # Check state file - should only have 10 entries
        with open(self.state_file) as f:
            data = json.load(f)
            assert len(data["task_hashes"]) <= 10
            assert data["cache_size"] == 10

    def test_hash_is_deterministic(self):
        """Test that same task produces same hash"""
        task = "Same task content"
        hash1 = self.dedupe.is_duplicate(task)[1]
        hash2 = self.dedupe.is_duplicate(task)[1]
        assert hash1 == hash2

    def test_different_tasks_produce_different_hashes(self):
        """Test different tasks produce different hashes"""
        hash1 = self.dedupe.is_duplicate("Task A")[1]
        hash2 = self.dedupe.is_duplicate("Task B")[1]
        assert hash1 != hash2


class TestClaudeBridge:
    """ClaudeBridge integration tests (mock tmux)"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        # Create subdirectory to avoid polluting real AI_SWARM_DIR
        self.test_dir = os.path.join(self.temp_dir, "test_swarm")
        os.makedirs(self.test_dir, exist_ok=True)

        self.env_patcher = patch.dict(
            os.environ,
            {
                'AI_SWARM_DIR': self.test_dir,
                'AI_SWARM_INTERACTIVE': '1',
                'AI_SWARM_BRIDGE_SESSION': 'test-session',
                'AI_SWARM_BRIDGE_WINDOW': 'master'
            }
        )
        self.env_patcher.start()

    def teardown_method(self):
        self.env_patcher.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('subprocess.run')
    def test_capture_pane(self, mock_run):
        """Test capture-pane call"""
        mock_run.return_value.stdout = "/task Test task\nOther line"

        bridge = ClaudeBridge()
        result = bridge._capture_pane()

        assert "Test task" in result
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == 'tmux'
        assert args[1] == 'capture-pane'
        # Verify default lines
        assert '-S' in args
        assert '-200' in args

    @patch('subprocess.run')
    @patch('swarm.claude_bridge.write_to_fifo_nonblocking')
    def test_task_extraction(self, mock_fifo, mock_run):
        """Test task extraction from capture output"""
        mock_run.return_value.stdout = (
            "Claude: Starting...\n"
            "/task Implement feature X\n"
            "Other output\n"
        )
        mock_fifo.return_value = True

        bridge = ClaudeBridge()

        tasks = []
        for line in bridge._capture_pane().split('\n'):
            task = bridge.parser.parse(line)
            if task:
                tasks.append(task)

        assert len(tasks) == 1
        assert tasks[0] == "Implement feature X"

    @patch('subprocess.run')
    def test_get_pane_spec_with_pane_id(self, mock_run):
        """Test pane spec generation with pane_id"""
        mock_run.return_value.stdout = ""

        with patch.dict(os.environ, {'AI_SWARM_BRIDGE_PANE': '%3'}):
            bridge = ClaudeBridge()
            assert bridge._get_pane_spec() == "%3"

    @patch('subprocess.run')
    def test_get_pane_spec_with_window(self, mock_run):
        """Test pane spec generation with session:window"""
        mock_run.return_value.stdout = ""

        bridge = ClaudeBridge()
        assert bridge._get_pane_spec() == "test-session:master"

    @patch('subprocess.run')
    def test_process_capture_empty(self, mock_run):
        """Test processing empty capture"""
        mock_run.return_value.stdout = ""

        bridge = ClaudeBridge()
        result = bridge._process_capture("")
        assert result == 0

    @patch('subprocess.run')
    @patch('swarm.claude_bridge.write_to_fifo_nonblocking')
    def test_process_capture_with_tasks(self, mock_fifo, mock_run):
        """Test processing capture with tasks"""
        mock_run.return_value.stdout = (
            "/task Task A\n"
            "/task Task B\n"
        )
        mock_fifo.return_value = True

        bridge = ClaudeBridge()
        result = bridge._process_capture(mock_run.return_value.stdout)

        assert result == 2
        assert mock_fifo.call_count == 2

    @patch('subprocess.run')
    @patch('swarm.claude_bridge.write_to_fifo_nonblocking')
    def test_process_capture_with_duplicates(self, mock_fifo, mock_run):
        """Test processing capture with duplicate tasks"""
        mock_run.return_value.stdout = (
            "/task Task A\n"
            "/task Task A\n"  # Duplicate
        )
        mock_fifo.return_value = True

        bridge = ClaudeBridge()
        result = bridge._process_capture(mock_run.return_value.stdout)

        # Only one task should be sent (first one)
        assert result == 1
        assert mock_fifo.call_count == 1


class TestTaskParserEdgeCases:
    """Edge case tests for TaskParser"""

    def setup_method(self):
        self.parser = TaskParser()

    def test_whitespace_handling(self):
        """Test various whitespace scenarios"""
        # Multiple spaces
        assert self.parser.parse("/task   Multiple   spaces") == "Multiple   spaces"

        # Tabs
        assert self.parser.parse("/task\tTabbed") == "Tabbed"

        # Mixed whitespace
        assert self.parser.parse("  /task  Mixed  ") == "Mixed"

    def test_special_characters_in_prompt(self):
        """Test special characters in task prompts"""
        # Quotes
        prompt = 'Task with "quotes"'
        assert self.parser.parse(f"/task {prompt}") == prompt

        # Backticks
        prompt = "Task with `code`"
        assert self.parser.parse(f"/task {prompt}") == prompt

        # Newlines (shouldn't happen in single line)
        # Handled by split('\n') before parsing

    def test_unicode_in_prompt(self):
        """Test unicode characters in prompts"""
        # Chinese
        assert self.parser.parse("/task 中文任务") == "中文任务"

        # Emoji
        assert self.parser.parse("/task Task with emoji 🚀") == "Task with emoji 🚀"

    def test_very_long_task(self):
        """Test very long task prompts"""
        long_task = "A" * 10000
        assert self.parser.parse(f"/task {long_task}") == long_task


class TestLineFilter:
    """LineFilter unit tests"""

    def setup_method(self):
        self.filter = LineFilter()

    def test_ignores_bridge_logging(self):
        """Test ignoring Bridge logging lines"""
        assert self.filter.should_ignore("[Bridge] Starting bridge...") is True
        assert self.filter.should_ignore("[Bridge] FIFO write success") is True
        assert self.filter.should_ignore("[Bridge] Task dispatched") is True

    def test_ignores_fifo_logging(self):
        """Test ignoring FIFO logging lines"""
        assert self.filter.should_ignore("[FIFO] Created task") is True
        assert self.filter.should_ignore("[FIFO] Task queued") is True

    def test_ignores_dispatched_logging(self):
        """Test ignoring DISPATCHED logging lines"""
        assert self.filter.should_ignore("[DISPATCHED] Task sent to FIFO") is True
        assert self.filter.should_ignore("-> FIFO: Task description") is True

    def test_ignores_claude_echo(self):
        """Test ignoring Claude echo patterns"""
        assert self.filter.should_ignore("Sure, I will help you") is True
        assert self.filter.should_ignore("Sure I will process this") is True
        assert self.filter.should_ignore("I'll help with that") is True
        assert self.filter.should_ignore("Here's what I found:") is True
        assert self.filter.should_ignore("[THINKING] Processing...") is True
        assert self.filter.should_ignore("{ \"result\": \"success\" }") is True
        assert self.filter.should_ignore("Thinking...") is True
        assert self.filter.should_ignore("Analyzing...") is True

    def test_allows_valid_task(self):
        """Test allowing valid task lines"""
        assert self.filter.should_ignore("/task Review PR #123") is False
        assert self.filter.should_ignore("TASK: Fix bug in login") is False
        assert self.filter.should_ignore("  /task Test task") is False

    def test_preserves_task_lines(self):
        """Test that task lines are not filtered out"""
        # TaskParser will still parse these, filter just ignores specific patterns
        # Lines that match task patterns should pass through
        pass  # Actual parsing tested in TestTaskParser


class TestSendKeys:
    """send-keys unit tests (mock tmux)"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_dir = os.path.join(self.temp_dir, "test_swarm")
        os.makedirs(self.test_dir, exist_ok=True)

        self.env_patcher = patch.dict(
            os.environ,
            {
                'AI_SWARM_DIR': self.test_dir,
                'AI_SWARM_INTERACTIVE': '1',
                'AI_SWARM_BRIDGE_SESSION': 'test-session',
                'AI_SWARM_BRIDGE_WINDOW': 'master'
            }
        )
        self.env_patcher.start()

    def teardown_method(self):
        self.env_patcher.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('subprocess.run')
    def test_send_keys_calls_tmux(self, mock_run):
        """Test that send-keys calls tmux correctly"""
        mock_run.return_value = MagicMock()

        bridge = ClaudeBridge()
        result = bridge._send_keys("test message")

        assert result is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == 'tmux'
        assert args[1] == 'send-keys'
        assert '-t' in args
        assert 'Enter' in args
        # Message should be passed directly without extra quotes
        assert 'test message' in args

    @patch('subprocess.run')
    def test_send_keys_with_special_chars(self, mock_run):
        """Test send-keys with special characters"""
        mock_run.return_value = MagicMock()

        bridge = ClaudeBridge()
        # Should handle quotes without breaking
        result = bridge._send_keys('Task with "quotes"')

        assert result is True

    @patch('subprocess.run')
    def test_send_keys_error_handling(self, mock_run):
        """Test send-keys error handling"""
        import subprocess
        mock_run.side_effect = Exception("tmux error")

        bridge = ClaudeBridge()
        result = bridge._send_keys("test")

        assert result is False


class TestDispatchFlow:
    """End-to-end dispatch flow tests (mock tmux)"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_dir = os.path.join(self.temp_dir, "test_swarm")
        os.makedirs(self.test_dir, exist_ok=True)

        self.env_patcher = patch.dict(
            os.environ,
            {
                'AI_SWARM_DIR': self.test_dir,
                'AI_SWARM_INTERACTIVE': '1',
                'AI_SWARM_BRIDGE_SESSION': 'test-session',
                'AI_SWARM_BRIDGE_WINDOW': 'master'
            }
        )
        self.env_patcher.start()

    def teardown_method(self):
        self.env_patcher.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('swarm.claude_bridge.subprocess.run')
    @patch('swarm.claude_bridge.write_to_fifo_nonblocking')
    def test_dispatch_with_send_keys_confirmation(
        self, mock_fifo, mock_run
    ):
        """Test that dispatch includes send-keys confirmation"""
        mock_run.return_value = MagicMock()
        mock_fifo.return_value = True

        bridge = ClaudeBridge()

        # Process a task
        result = bridge._write_to_fifo("Test task for dispatch")

        # FIFO should be called
        assert mock_fifo.called

        # send-keys should be called (via _send_keys in _write_to_fifo)
        # Check that tmux send-keys was called
        send_keys_calls = [
            c for c in mock_run.call_args_list
            if len(c.args) > 0 and c.args[0][0] == 'tmux' and c.args[0][1] == 'send-keys'
        ]
        assert len(send_keys_calls) >= 1

    @patch('swarm.claude_bridge.subprocess.run')
    @patch('swarm.claude_bridge.write_to_fifo_nonblocking')
    def test_dispatch_message_format(
        self, mock_fifo, mock_run
    ):
        """Test that dispatch message has correct format"""
        mock_run.return_value = MagicMock()
        mock_fifo.return_value = True

        bridge = ClaudeBridge()
        bridge._write_to_fifo("My test task")

        # Find the send-keys call
        send_keys_found = False
        for c in mock_run.call_args_list:
            if len(c.args) > 0 and 'send-keys' in c.args[0]:
                # Check that message contains [DISPATCHED]
                msg_arg = [a for a in c.args[0] if '[DISPATCHED]' in a]
                assert len(msg_arg) >= 1
                send_keys_found = True
                break
        assert send_keys_found, "send-keys call not found"

    @patch('subprocess.run')
    def test_bridge_output_filtered(self, mock_run):
        """Test that Bridge's own output is filtered out"""
        mock_run.return_value = MagicMock()

        bridge = ClaudeBridge()

        # These should be filtered
        lines = [
            "[Bridge] Starting bridge...",
            "[FIFO] Task created",
            "[DISPATCHED] Task sent",
            "-> FIFO: Task description",
        ]

        for line in lines:
            assert bridge.parser.filter.should_ignore(line) is True

        # Valid tasks should pass
        lines_should_pass = [
            "/task Review PR #123",
            "TASK: Fix bug",
        ]

        for line in lines_should_pass:
            assert bridge.parser.filter.should_ignore(line) is False
