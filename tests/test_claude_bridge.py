#!/usr/bin/env python3
"""
Unit tests for claude_bridge.py
"""

import pytest
import tempfile
import os
import json
from unittest.mock import patch, MagicMock

from swarm.claude_bridge import (
    TaskParser,
    DedupeState,
    ClaudeBridge,
    LineFilter,
    BridgePhase,
    BridgeTaskIdGenerator,
    DispatchMode,
    BridgeDispatchError,
)


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


class TestBridgeTaskIdGenerator:
    """BridgeTaskIdGenerator unit tests"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.id_file = os.path.join(self.temp_dir, "task_ids.txt")

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generates_unique_ids(self):
        """Test that generated IDs are unique"""
        generator = BridgeTaskIdGenerator(self.id_file)
        ids = [generator.generate() for _ in range(100)]
        assert len(ids) == len(set(ids)), "IDs should be unique"

    def test_id_format(self):
        """Test ID format: br-{unix_ns}-{3-char_suffix}"""
        import re
        generator = BridgeTaskIdGenerator(self.id_file)
        task_id = generator.generate()

        # Check format matches br-{ns}-{3chars}
        pattern = r'^br-\d{19}-[a-z0-9]{3}$'
        assert re.match(pattern, task_id), f"ID format mismatch: {task_id}"

    def test_id_prefix(self):
        """Test that IDs start with 'br-'"""
        generator = BridgeTaskIdGenerator(self.id_file)
        for _ in range(10):
            assert generator.generate().startswith('br-')

    def test_thread_safety(self):
        """Test thread-safe ID generation"""
        import threading

        generator = BridgeTaskIdGenerator(self.id_file)
        ids = []
        errors = []

        def generate_ids():
            try:
                for _ in range(50):
                    ids.append(generator.generate())
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=generate_ids) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread errors: {errors}"
        assert len(ids) == 200, f"Expected 200 IDs, got {len(ids)}"
        assert len(ids) == len(set(ids)), "IDs should be unique across threads"

    def test_persistence(self):
        """Test ID persistence across instances"""
        generator1 = BridgeTaskIdGenerator(self.id_file)
        ids1 = [generator1.generate() for _ in range(5)]

        # Create new generator (simulating restart)
        generator2 = BridgeTaskIdGenerator(self.id_file)
        new_id = generator2.generate()

        # New ID should be unique
        assert new_id not in ids1, "New ID should not duplicate previous IDs"


class TestAckDetection:
    """ACK detection unit tests"""

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
                'AI_SWARM_BRIDGE_WINDOW': 'master',
                'AI_SWARM_BRIDGE_ACK_TIMEOUT': '0.5',  # Short timeout for tests
            }
        )
        self.env_patcher.start()

    def teardown_method(self):
        self.env_patcher.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('subprocess.run')
    def test_wait_for_ack_with_explicit_ack_marker(self, mock_run):
        """Test ACK detection: explicit [ACK: {id}] marker"""
        bridge = ClaudeBridge()

        with patch.object(bridge, '_capture_worker_pane') as mock_capture:
            # Explicit ACK marker (highest confidence)
            mock_capture.return_value = "[BRIDGE_TASK_ID: br-123] TASK: Fix the bug\n[ACK: br-123]"
            ack_received, latency_ms = bridge._wait_for_ack("br-123", '%0', baseline_line_count=0, timeout=0.1)

        assert ack_received is True
        assert latency_ms >= 0

    @patch('subprocess.run')
    def test_wait_for_ack_with_started_marker(self, mock_run):
        """Test ACK detection: explicit [STARTED: {id}] marker"""
        bridge = ClaudeBridge()

        with patch.object(bridge, '_capture_worker_pane') as mock_capture:
            # Explicit STARTED marker
            mock_capture.return_value = "[BRIDGE_TASK_ID: br-456] TASK: Write tests\n[STARTED: br-456]"
            ack_received, latency_ms = bridge._wait_for_ack("br-456", '%0', baseline_line_count=0, timeout=0.1)

        assert ack_received is True

    @patch('subprocess.run')
    def test_wait_for_ack_with_processing_signal_after_marker(self, mock_run):
        """Test ACK detection: dispatch marker + processing signal AFTER marker"""
        bridge = ClaudeBridge()

        with patch.object(bridge, '_capture_worker_pane') as mock_capture:
            # Dispatch marker + Claude's "I'll help..." AFTER marker
            # This is key: processing signal must be AFTER the marker, not in history
            mock_capture.return_value = "[BRIDGE_TASK_ID: br-123] TASK: Fix the bug\nI'll help you with that."
            ack_received, latency_ms = bridge._wait_for_ack("br-123", '%0', baseline_line_count=1, timeout=0.1)

        assert ack_received is True

    @patch('subprocess.run')
    def test_wait_for_ack_with_thinking_after_marker(self, mock_run):
        """Test ACK detection: dispatch marker + [THINKING] AFTER marker"""
        bridge = ClaudeBridge()

        with patch.object(bridge, '_capture_worker_pane') as mock_capture:
            # Dispatch marker + [THINKING] AFTER marker
            mock_capture.return_value = "[BRIDGE_TASK_ID: br-456] TASK: Write tests\n[THINKING]"
            ack_received, latency_ms = bridge._wait_for_ack("br-456", '%0', baseline_line_count=1, timeout=0.1)

        assert ack_received is True

    @patch('subprocess.run')
    def test_wait_for_ack_timeout_no_dispatch_marker(self, mock_run):
        """Test ACK timeout when dispatch marker not present"""
        bridge = ClaudeBridge()

        with patch.object(bridge, '_capture_worker_pane') as mock_capture:
            # No dispatch marker
            mock_capture.return_value = "Worker busy..."
            ack_received, elapsed_ms = bridge._wait_for_ack("br-123", '%0', baseline_line_count=0, timeout=0.1)

        assert ack_received is False
        assert elapsed_ms >= 90  # Allow some tolerance

    @patch('subprocess.run')
    def test_wait_for_ack_timeout_marker_only_no_processing_signal(self, mock_run):
        """Test ACK timeout when only dispatch marker, NO processing signal AFTER it

        This is the critical test case for the false positive fix:
        - Marker is present
        - But marker is on its own line (no new content after it)
        - Must NOT falsely ACK
        """
        bridge = ClaudeBridge()

        with patch.object(bridge, '_capture_worker_pane') as mock_capture:
            # Only dispatch marker on its own line, NO processing signal after
            mock_capture.return_value = "[BRIDGE_TASK_ID: br-123] TASK: Fix the bug"
            ack_received, elapsed_ms = bridge._wait_for_ack("br-123", '%0', baseline_line_count=0, timeout=0.1)

        assert ack_received is False  # CRITICAL: must be False!
        assert elapsed_ms >= 90

    @patch('subprocess.run')
    def test_wait_for_ack_false_positive_history_content(self, mock_run):
        """Test ACK false positive: marker + existing history content (NOT after marker)

        This is the key test case from Codex review:
        - Worker pane has existing welcome/history content (many lines)
        - Dispatch marker is present
        - But processing signals are NOT in content AFTER the marker
        - Must NOT falsely ACK
        """
        bridge = ClaudeBridge()

        # Simulate: pane has 10 lines of history, then dispatch marker appears
        # But no processing signal AFTER the dispatch marker
        with patch.object(bridge, '_capture_worker_pane') as mock_capture:
            mock_capture.return_value = """Welcome to Claude Code
Last login: ...
History buffer line 3
History buffer line 4
History buffer line 5
History buffer line 6
History buffer line 7
History buffer line 8
History buffer line 9
History buffer line 10
[BRIDGE_TASK_ID: br-999] TASK: Some task"""
            ack_received, elapsed_ms = bridge._wait_for_ack("br-999", '%0', baseline_line_count=10, timeout=0.1)

        assert ack_received is False  # CRITICAL: must be False!
        # Processing signal must be AFTER marker, not in history

    @patch('subprocess.run')
    def test_wait_for_ack_true_positive_new_content_after_marker(self, mock_run):
        """Test ACK success: existing history + NEW processing content AFTER marker

        This is the success case:
        - Worker pane has history
        - Dispatch marker appears
        - NEW processing content appears AFTER marker
        - Must ACK successfully
        """
        bridge = ClaudeBridge()

        with patch.object(bridge, '_capture_worker_pane') as mock_capture:
            # History content, then dispatch marker, then new processing content
            mock_capture.return_value = """Welcome to Claude Code
Last login: ...
[BRIDGE_TASK_ID: br-888] TASK: Fix the bug
I'll help you with that."""
            ack_received, latency_ms = bridge._wait_for_ack("br-888", '%0', baseline_line_count=2, timeout=0.1)

        assert ack_received is True

    @patch('subprocess.run')
    def test_wait_for_ack_task_text_with_sure_no_new_content(self, mock_run):
        """Test critical false positive: TASK: Sure, ... with NO new output after

        This is the key test case from Codex review:
        - Task text contains "Sure" (processing signal word)
        - But there's no NEW content after the dispatch marker
        - Must NOT falsely ACK
        """
        bridge = ClaudeBridge()

        with patch.object(bridge, '_capture_worker_pane') as mock_capture:
            # Task text contains "Sure" but no new content after marker
            # baseline=1 (before dispatch), current=2 (marker + task line only)
            mock_capture.return_value = "[BRIDGE_TASK_ID: br-test-3] TASK: Sure, do nothing"
            # This should timeout because:
            # 1. TASK line stripped
            # 2. No new content after task line
            # 3. Line count increased only by dispatch (1 -> 2), not by processing
            ack_received, elapsed_ms = bridge._wait_for_ack("br-test-3", '%0', baseline_line_count=1, timeout=0.1)

        assert ack_received is False  # CRITICAL: must be False!
        assert elapsed_ms >= 90

    @patch('subprocess.run')
    def test_wait_for_ack_task_text_with_sure_and_new_content(self, mock_run):
        """Test true positive: TASK: Sure, ... WITH new content after

        This verifies the fix still allows real ACKs:
        - Task text contains "Sure"
        - There IS new content after the task line
        - Must ACK successfully
        """
        bridge = ClaudeBridge()

        with patch.object(bridge, '_capture_worker_pane') as mock_capture:
            # Task text contains "Sure" AND there's real new content after
            mock_capture.return_value = """[BRIDGE_TASK_ID: br-real-1] TASK: Sure, do this
I'll help you with that right away."""
            # This should succeed because:
            # 1. TASK line stripped
            # 2. New content exists ("I'll help...")
            # 3. Line count increased by processing content
            ack_received, latency_ms = bridge._wait_for_ack("br-real-1", '%0', baseline_line_count=1, timeout=0.1)

        assert ack_received is True


class TestRetryLogic:
    """Retry logic unit tests"""

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
                'AI_SWARM_BRIDGE_WINDOW': 'master',
                'AI_SWARM_BRIDGE_MAX_RETRIES': '2',
                'AI_SWARM_BRIDGE_RETRY_DELAY': '0.0',  # No delay in tests
            }
        )
        self.env_patcher.start()

    def teardown_method(self):
        self.env_patcher.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_retry_on_ack_failure(self):
        """Test retry mechanism when ACK not received"""
        bridge = ClaudeBridge()

        # The retry logic is in _dispatch_to_worker
        # Verify that retry delays are configurable
        assert hasattr(bridge, 'retry_delay')
        assert hasattr(bridge, 'max_retries')

    def test_max_retries_exhausted(self):
        """Test that BridgeDispatchError is raised after max retries"""
        bridge = ClaudeBridge()

        with patch.object(bridge, '_get_worker_panes') as mock_panes:
            mock_panes.return_value = ['%0', '%1']

            with patch.object(bridge, '_send_text_to_pane') as mock_send:
                mock_send.return_value = True

                with patch.object(bridge, '_capture_worker_pane') as mock_capture:
                    # Never ACK
                    mock_capture.return_value = "Worker busy..."

                    with pytest.raises(BridgeDispatchError) as exc_info:
                        bridge._dispatch_to_worker("Test task", "br-123")

                    assert "br-123" in str(exc_info.value)


class TestStructuredLogging:
    """Structured logging unit tests"""

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
                'AI_SWARM_BRIDGE_WINDOW': 'master',
            }
        )
        self.env_patcher.start()

    def teardown_method(self):
        self.env_patcher.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_log_phase_format(self):
        """Test structured log format"""
        import json
        from datetime import datetime, timezone

        bridge = ClaudeBridge()
        bridge.ai_swarm_dir = self.test_dir  # Use temp dir

        bridge._log_phase(
            phase=BridgePhase.DISPATCHED,
            bridge_task_id="br-123456-abc",
            task_preview="Test task",
            target_worker="%0",
            attempt=1,
            dispatch_mode=DispatchMode.DIRECT
        )

        # Read bridge.log
        log_file = os.path.join(self.test_dir, 'bridge.log')
        with open(log_file, 'r') as f:
            line = f.readline().strip()

        # Parse JSON
        entry = json.loads(line)

        # Verify structure
        assert 'ts' in entry
        assert entry['phase'] == 'DISPATCHED'
        assert entry['bridge_task_id'] == 'br-123456-abc'
        assert entry['task_preview'] == 'Test task'
        assert entry['target_worker'] == '%0'
        assert entry['attempt'] == 1
        assert entry['dispatch_mode'] == 'direct'

    def test_log_phase_json_format(self):
        """Test that bridge.log is valid JSON per line"""
        import json

        bridge = ClaudeBridge()
        bridge.ai_swarm_dir = self.test_dir

        # Write multiple phase logs
        for phase in [BridgePhase.CAPTURED, BridgePhase.PARSED, BridgePhase.DISPATCHED]:
            bridge._log_phase(
                phase=phase,
                bridge_task_id="br-test-123",
                task_preview="Test"
            )

        # Read and parse each line
        log_file = os.path.join(self.test_dir, 'bridge.log')
        with open(log_file, 'r') as f:
            for line in f:
                entry = json.loads(line.strip())
                assert 'ts' in entry
                assert 'phase' in entry


class TestStatusLogMeta:
    """Status log meta fields unit tests"""

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
                'AI_SWARM_BRIDGE_WINDOW': 'master',
            }
        )
        self.env_patcher.start()

    def teardown_method(self):
        self.env_patcher.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_dispatch_mode_enum(self):
        """Test DispatchMode enum values"""
        assert DispatchMode.FIFO == "fifo"
        assert DispatchMode.DIRECT == "direct"
        assert DispatchMode.DIRECT_FALLBACK == "direct_fallback"

    def test_bridge_phase_enum(self):
        """Test BridgePhase enum values"""
        assert BridgePhase.CAPTURED == "CAPTURED"
        assert BridgePhase.PARSED == "PARSED"
        assert BridgePhase.DISPATCHED == "DISPATCHED"
        assert BridgePhase.ACKED == "ACKED"
        assert BridgePhase.RETRY == "RETRY"
        assert BridgePhase.FAILED == "FAILED"

    def test_log_phase_includes_meta(self):
        """Test that _log_phase includes meta fields for status.log"""
        import json

        bridge = ClaudeBridge()
        bridge.ai_swarm_dir = self.test_dir

        # Mock broadcaster to capture meta
        with patch('swarm.status_broadcaster.StatusBroadcaster') as MockBroadcaster:
            mock_bc = MagicMock()
            MockBroadcaster.return_value = mock_bc

            bridge._log_phase(
                phase=BridgePhase.DISPATCHED,
                bridge_task_id="br-meta-test",
                task_preview="Test task",
                target_worker="%4",
                attempt=3,
                dispatch_mode=DispatchMode.FIFO
            )

            # Verify broadcast was called with meta
            mock_bc.broadcast.assert_called_once()
            call_kwargs = mock_bc.broadcast.call_args[1]

            assert call_kwargs['meta']['type'] == 'BRIDGE'
            assert call_kwargs['meta']['bridge_phase'] == 'DISPATCHED'
            assert call_kwargs['meta']['bridge_task_id'] == 'br-meta-test'
            assert call_kwargs['meta']['target_worker'] == '%4'
            assert call_kwargs['meta']['attempt'] == 3
            assert call_kwargs['meta']['dispatch_mode'] == 'fifo'

    def test_bridge_dispatch_error(self):
        """Test BridgeDispatchError attributes"""
        attempts = [
            ('%0', False, 1000.0, 'ack_timeout'),
            ('%1', False, 2000.0, 'ack_timeout'),
        ]
        error = BridgeDispatchError('br-err-test', attempts, 'all retries exhausted')

        assert error.task_id == 'br-err-test'
        assert len(error.attempts) == 2
        assert 'br-err-test' in str(error)


class TestCaptureWorkerPane:
    """_capture_worker_pane unit tests"""

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
                'AI_SWARM_BRIDGE_WINDOW': 'master',
            }
        )
        self.env_patcher.start()

    def teardown_method(self):
        self.env_patcher.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('subprocess.run')
    def test_capture_worker_pane(self, mock_run):
        """Test worker pane capture"""
        mock_run.return_value.stdout = "Thinking...\n[ACK] br-123"

        bridge = ClaudeBridge()
        result = bridge._capture_worker_pane('%0')

        assert "br-123" in result
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_capture_worker_pane_error(self, mock_run):
        """Test worker pane capture error handling"""
        mock_run.side_effect = Exception("tmux error")

        bridge = ClaudeBridge()
        result = bridge._capture_worker_pane('%0')

        assert result == ""


class TestDispatchModeTracking:
    """Dispatch mode tracking tests"""

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
                'AI_SWARM_BRIDGE_WINDOW': 'master',
            }
        )
        self.env_patcher.start()

    def teardown_method(self):
        self.env_patcher.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_bridge_init_includes_config(self):
        """Test that bridge initializes with ACK and retry config"""
        bridge = ClaudeBridge()

        # ACK configuration
        assert hasattr(bridge, 'ack_timeout')
        assert bridge.ack_timeout == 10.0  # Default

        # Retry configuration
        assert hasattr(bridge, 'max_retries')
        assert hasattr(bridge, 'retry_delay')

    @patch('subprocess.run')
    @patch('swarm.claude_bridge.write_to_fifo_nonblocking')
    def test_fifo_dispatch_with_logging(self, mock_fifo, mock_run):
        """Test FIFO dispatch includes structured logging"""
        mock_fifo.return_value = True
        mock_run.return_value = MagicMock()

        bridge = ClaudeBridge()
        bridge.ai_swarm_dir = self.test_dir

        # Process a task
        result = bridge._write_to_fifo("Test task for logging")

        # Verify result
        assert result is True

        # Verify bridge.log was created with JSON format
        log_file = os.path.join(self.test_dir, 'bridge.log')
        assert os.path.exists(log_file)

        with open(log_file, 'r') as f:
            for line in f:
                entry = json.loads(line.strip())
                assert 'ts' in entry
                assert 'phase' in entry


class TestPhaseTransitions:
    """Phase transition tests"""

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
                'AI_SWARM_BRIDGE_WINDOW': 'master',
            }
        )
        self.env_patcher.start()

    def teardown_method(self):
        self.env_patcher.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_all_phases_logged(self):
        """Test that all phases can be logged"""
        bridge = ClaudeBridge()
        bridge.ai_swarm_dir = self.test_dir

        # Log all phases
        for phase in [
            BridgePhase.CAPTURED,
            BridgePhase.PARSED,
            BridgePhase.DISPATCHED,
            BridgePhase.ACKED,
            BridgePhase.RETRY,
            BridgePhase.FAILED
        ]:
            bridge._log_phase(
                phase=phase,
                bridge_task_id=f"br-phase-{phase}",
                task_preview="Test task"
            )

        # Verify all logged
        log_file = os.path.join(self.test_dir, 'bridge.log')
        with open(log_file, 'r') as f:
            lines = f.readlines()

        assert len(lines) == 6

        # Each line should be valid JSON with correct phase
        for line in lines:
            entry = json.loads(line)
            assert 'phase' in entry

    def test_phase_with_latency(self):
        """Test logging phase with latency"""
        bridge = ClaudeBridge()
        bridge.ai_swarm_dir = self.test_dir

        bridge._log_phase(
            phase=BridgePhase.ACKED,
            bridge_task_id="br-latency-test",
            task_preview="Test",
            latency_ms=123.45
        )

        log_file = os.path.join(self.test_dir, 'bridge.log')
        with open(log_file, 'r') as f:
            entry = json.loads(f.readline())

        assert entry['latency_ms'] == 123.45


class TestDispatchFailureHandling:
    """Dispatch failure handling tests"""

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
                'AI_SWARM_BRIDGE_WINDOW': 'master',
                'AI_SWARM_BRIDGE_DIRECT_FALLBACK': '0',  # Disable direct fallback
            }
        )
        self.env_patcher.start()

    def teardown_method(self):
        self.env_patcher.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('subprocess.run')
    @patch('swarm.claude_bridge.write_to_fifo_nonblocking')
    def test_fifo_failure_no_fallback(self, mock_fifo, mock_run):
        """Test FIFO failure when direct fallback is disabled"""
        mock_fifo.return_value = False
        mock_run.return_value = MagicMock()

        bridge = ClaudeBridge()
        bridge.ai_swarm_dir = self.test_dir

        # Set cooldown to past to ensure error is logged
        bridge._last_fifo_error_time = 0

        # Process a task - should return False
        result = bridge._write_to_fifo("Test task")

        assert result is False

    def test_bridge_dispatch_error_creation(self):
        """Test BridgeDispatchError with all attributes"""
        attempts = [
            ('%0', False, 100.0, 'send_keys_failed'),
            ('%0', False, 200.0, 'ack_timeout'),
            ('%1', False, 300.0, 'ack_timeout'),
        ]
        error = BridgeDispatchError(
            task_id='br-error-test',
            attempts=attempts,
            last_error='max retries exceeded'
        )

        assert error.task_id == 'br-error-test'
        assert len(error.attempts) == 3
        assert error.last_error == 'max retries exceeded'
        # Check exception message
        assert 'br-error-test' in str(error)
        assert '3 attempts' in str(error)


class TestBridgeTaskIdGeneratorEdgeCases:
    """Edge case tests for BridgeTaskIdGenerator"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.id_file = os.path.join(self.temp_dir, "task_ids.txt")

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generate_without_file(self):
        """Test ID generation without persistence file"""
        generator = BridgeTaskIdGenerator()  # No file
        ids = [generator.generate() for _ in range(10)]

        # All IDs should be unique
        assert len(ids) == len(set(ids))

    def test_id_format(self):
        """Test that generated IDs have expected format"""
        import re

        generator = BridgeTaskIdGenerator()

        for _ in range(20):
            task_id = generator.generate()
            # Format: br-{timestamp}-{3 char suffix}
            # Timestamp: 18-19 digits (nanoseconds since epoch)
            # Pattern: br-<digits>-<alphanumeric>
            pattern = r'^br-\d{18,19}-[a-z0-9]{3}$'
            assert re.match(pattern, task_id), f"Invalid format: {task_id}"

    def test_suffix_characters(self):
        """Test that suffix uses only lowercase letters and digits"""
        import re
        generator = BridgeTaskIdGenerator()

        for _ in range(50):
            task_id = generator.generate()
            suffix = task_id.split('-')[-1]
            assert re.match(r'^[a-z0-9]+$', suffix), f"Invalid suffix: {suffix}"


class TestAckPatternMatching:
    """ACK pattern matching tests - verify patterns match correctly"""

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
                'AI_SWARM_BRIDGE_WINDOW': 'master',
            }
        )
        self.env_patcher.start()

    def teardown_method(self):
        self.env_patcher.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_dispatch_marker_pattern(self):
        """Test dispatch marker pattern matches correctly"""
        import re

        bridge = ClaudeBridge()
        bridge_task_id = "br-12345-xyz"

        # Pattern should match dispatch marker
        dispatch_pattern = re.compile(
            r'\[BRIDGE_TASK_ID:\s*' + re.escape(bridge_task_id) + r'\]'
        )

        # Should match dispatch marker
        assert dispatch_pattern.search(f"[BRIDGE_TASK_ID: {bridge_task_id}] TASK: Fix bug") is not None
        assert dispatch_pattern.search(f"[BRIDGE_TASK_ID:  {bridge_task_id}]") is not None  # Extra spaces

        # Should not match
        assert dispatch_pattern.search(f"[BRIDGE_TASK_ID: br-other-id]") is None

    def test_explicit_ack_pattern(self):
        """Test explicit [ACK: {id}] pattern"""
        import re

        bridge_task_id = "br-999-abc"
        ack_pattern = re.compile(r'\[ACK:\s*' + re.escape(bridge_task_id) + r'\]')

        # Should match
        assert ack_pattern.search(f"[ACK: {bridge_task_id}]") is not None
        assert ack_pattern.search(f"[ACK:  {bridge_task_id}]") is not None  # Extra spaces

        # Should not match
        assert ack_pattern.search(f"[ACK: br-other-id]") is None

    def test_explicit_started_pattern(self):
        """Test explicit [STARTED: {id}] pattern"""
        import re

        bridge_task_id = "br-888-xyz"
        started_pattern = re.compile(r'\[STARTED:\s*' + re.escape(bridge_task_id) + r'\]')

        # Should match
        assert started_pattern.search(f"[STARTED: {bridge_task_id}]") is not None
        assert started_pattern.search(f"[STARTED:  {bridge_task_id}]") is not None

        # Should not match
        assert started_pattern.search(f"[STARTED: br-other-id]") is None

    def test_processing_signal_patterns(self):
        """Test processing signal patterns match correctly"""
        import re

        processing_signal_patterns = [
            re.compile(r"I'll\s+", re.IGNORECASE),
            re.compile(r"Sure,?\s+", re.IGNORECASE),
            re.compile(r"Okay,?\s+", re.IGNORECASE),
            re.compile(r'\[THINKING\]', re.IGNORECASE),
            re.compile(r'\[THOUGHT\]', re.IGNORECASE),
        ]

        # These should match
        assert processing_signal_patterns[0].search("I'll help you") is not None
        assert processing_signal_patterns[1].search("Sure, I can") is not None
        assert processing_signal_patterns[2].search("Okay let me") is not None
        assert processing_signal_patterns[3].search("[THINKING]") is not None
        assert processing_signal_patterns[4].search("[THOUGHT] analyzing...") is not None

    @patch('subprocess.run')
    def test_ack_with_special_chars_in_id(self, mock_run):
        """Test ACK detection with special characters in ID and Claude response"""
        mock_run.return_value.stdout = "output"

        bridge = ClaudeBridge()
        bridge_task_id = "br-123-abc"  # Normal ID

        with patch.object(bridge, '_capture_worker_pane') as mock_capture:
            # Dispatch marker + Claude response AFTER marker
            mock_capture.return_value = f"[BRIDGE_TASK_ID: {bridge_task_id}] TASK: Fix bug\nI'll help you with that."
            ack_received, _ = bridge._wait_for_ack(bridge_task_id, '%0', baseline_line_count=1, timeout=0.1)

        assert ack_received is True


class TestErrorHandlingPaths:
    """Error handling path tests"""

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
                'AI_SWARM_BRIDGE_WINDOW': 'master',
            }
        )
        self.env_patcher.start()

    def teardown_method(self):
        self.env_patcher.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('subprocess.run')
    def test_capture_pane_timeout(self, mock_run):
        """Test capture pane timeout handling"""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("test", 5)

        bridge = ClaudeBridge()
        result = bridge._capture_pane()

        assert result == ""

    @patch('subprocess.run')
    def test_capture_pane_file_not_found(self, mock_run):
        """Test capture pane tmux not found"""
        mock_run.side_effect = FileNotFoundError("tmux not found")

        bridge = ClaudeBridge()
        result = bridge._capture_pane()

        assert result == ""

    @patch('subprocess.run')
    def test_send_keys_timeout(self, mock_run):
        """Test send-keys timeout handling"""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("test", 5)

        bridge = ClaudeBridge()
        result = bridge._send_keys("test")

        assert result is False

    @patch('subprocess.run')
    def test_send_keys_file_not_found(self, mock_run):
        """Test send-keys tmux not found"""
        mock_run.side_effect = FileNotFoundError("tmux not found")

        bridge = ClaudeBridge()
        result = bridge._send_keys("test")

        assert result is False

    @patch('subprocess.run')
    def test_send_text_to_pane_error(self, mock_run):
        """Test send text to pane error handling"""
        mock_run.side_effect = Exception("tmux error")

        bridge = ClaudeBridge()
        result = bridge._send_text_to_pane('%0', "test")

        assert result is False

    @patch('subprocess.run')
    def test_get_worker_panes_error(self, mock_run):
        """Test get worker panes error handling"""
        mock_run.side_effect = Exception("tmux error")

        bridge = ClaudeBridge()
        result = bridge._get_worker_panes()

        assert result == []

    @patch('subprocess.run')
    def test_get_worker_panes_nonzero_return(self, mock_run):
        """Test get worker panes with non-zero return"""
        mock_run.return_value = MagicMock(returncode=1)

        bridge = ClaudeBridge()
        result = bridge._get_worker_panes()

        assert result == []


class TestDedupeWithFileErrors:
    """Dedupe state with file error handling tests"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = os.path.join(self.temp_dir, "dedupe.json")

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_dedupe_with_corrupted_file(self):
        """Test dedupe handles corrupted state file"""
        # Write corrupted JSON
        with open(self.state_file, 'w') as f:
            f.write("{ invalid json }")

        # Should not raise, should handle gracefully
        dedupe = DedupeState(self.state_file)

        # Should be empty (graceful failure)
        is_dup, hash_id = dedupe.is_duplicate("test task")
        assert is_dup is False

    def test_dedupe_with_permission_error(self):
        """Test dedupe handles permission error gracefully"""
        import os

        # Create directory (not file) at state_file path
        os.makedirs(self.state_file, exist_ok=True)

        # Should not raise, should handle gracefully
        dedupe = DedupeState(self.state_file)

        is_dup, hash_id = dedupe.is_duplicate("test task")
        assert is_dup is False


class TestBridgeTaskIdGeneratorFileErrors:
    """Task ID generator file error handling tests"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        # Create a directory where we expect a file
        self.id_file = os.path.join(self.temp_dir, "ids")
        os.makedirs(self.id_file, exist_ok=True)

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generator_with_permission_error(self):
        """Test generator handles file permission errors gracefully"""
        # id_file is a directory, so opening as file will fail
        generator = BridgeTaskIdGenerator(self.id_file)

        # Should not raise, should generate IDs
        ids = [generator.generate() for _ in range(5)]
        assert len(ids) == len(set(ids))


class TestLogPhaseFileErrors:
    """Log phase file error handling tests"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_dir = os.path.join(self.temp_dir, "test_swarm")
        # Create a file where we expect a directory
        os.makedirs(self.test_dir, exist_ok=True)

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_log_phase_with_write_error(self):
        """Test _log_phase handles write errors gracefully"""
        bridge = ClaudeBridge()
        # Set ai_swarm_dir to a file (not directory) to trigger write error
        bridge.ai_swarm_dir = os.path.join(self.temp_dir, "not_a_dir")

        # Should not raise
        bridge._log_phase(
            phase=BridgePhase.DISPATCHED,
            bridge_task_id="br-error-test",
            task_preview="Test"
        )
