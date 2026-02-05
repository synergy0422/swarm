#!/usr/bin/env python3
"""
Unit tests for fifo_input.py - FIFO input channel and command parsing

IMPORTANT: Tests must NOT pollute global state. Each test should:
- Not rely on importlib.reload (changes global state)
- Mock environment variables at test time, not module load time
- Use fixtures to reset state between tests
"""

import os
import sys
import stat
import tempfile
import pytest
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock


# Import functions and class (not module-level env-dependent constants)
from swarm.fifo_input import FifoInputHandler, get_fifo_path, get_interactive_mode


class TestGetFunctions:
    """Test helper functions with proper env isolation"""

    def test_get_fifo_path_default(self):
        """Test FIFO path uses default when AI_SWARM_DIR not set"""
        with patch.dict(os.environ, {}, clear=True):
            path = get_fifo_path()
            assert path == "/tmp/ai_swarm/master_inbox"

    def test_get_fifo_path_custom(self):
        """Test FIFO path respects AI_SWARM_DIR"""
        with patch.dict(os.environ, {"AI_SWARM_DIR": "/custom/path"}):
            path = get_fifo_path()
            assert path == "/custom/path/master_inbox"

    def test_get_interactive_mode_disabled(self):
        """Test interactive mode disabled by default"""
        env = {k: v for k, v in os.environ.items() if k != "AI_SWARM_INTERACTIVE"}
        with patch.dict(os.environ, env, clear=False):
            mode = get_interactive_mode()
            assert mode is False

    def test_get_interactive_mode_enabled(self):
        """Test interactive mode enabled with env var"""
        with patch.dict(os.environ, {"AI_SWARM_INTERACTIVE": "1"}):
            mode = get_interactive_mode()
            assert mode is True


class TestFifoInputHandler:
    """Tests for FifoInputHandler class"""

    @pytest.fixture
    def handler_with_isolated_env(self, tmp_path):
        """Create handler with isolated temp directory for AI_SWARM_DIR"""
        with patch.dict(os.environ, {"AI_SWARM_DIR": str(tmp_path)}):
            handler = FifoInputHandler()
            handler._broadcaster = MagicMock()
            return handler

    def test_parse_command_task_with_prefix(self, handler_with_isolated_env):
        """Test /task command parsing with prompt"""
        cmd, payload = handler_with_isolated_env._parse_command("/task review pr #123")
        assert cmd == "task"
        assert payload == "review pr #123"

    def test_parse_command_task_without_prompt_error(self, handler_with_isolated_env):
        """Test /task without prompt returns error"""
        cmd, payload = handler_with_isolated_env._parse_command("/task")
        assert cmd == "error"
        assert "requires a prompt" in payload

    def test_parse_command_help(self, handler_with_isolated_env):
        """Test /help command parsing"""
        cmd, payload = handler_with_isolated_env._parse_command("/help")
        assert cmd == "help"
        assert payload is None

    def test_parse_command_quit(self, handler_with_isolated_env):
        """Test /quit command parsing"""
        cmd, payload = handler_with_isolated_env._parse_command("/quit")
        assert cmd == "quit"
        assert payload is None

    def test_parse_command_plain_text(self, handler_with_isolated_env):
        """Test plain text treated as task prompt"""
        cmd, payload = handler_with_isolated_env._parse_command("fix the login bug")
        assert cmd == "task"
        assert payload == "fix the login bug"

    def test_parse_command_empty_line(self, handler_with_isolated_env):
        """Test empty line is ignored"""
        cmd, payload = handler_with_isolated_env._parse_command("")
        assert cmd == "ignore"

    def test_parse_command_whitespace_only(self, handler_with_isolated_env):
        """Test whitespace-only line is ignored"""
        cmd, payload = handler_with_isolated_env._parse_command("   \n")
        assert cmd == "ignore"

    def test_parse_command_unknown(self, handler_with_isolated_env):
        """Test unknown command returns error"""
        cmd, payload = handler_with_isolated_env._parse_command("/unknown arg")
        assert cmd == "error"
        assert "Unknown command" in payload

    def test_handle_task_calls_queue(self, handler_with_isolated_env):
        """Test _handle_task calls TaskQueue.add_task"""
        handler_with_isolated_env._task_queue = MagicMock()
        handler_with_isolated_env._task_queue.add_task.return_value = "task_001"

        handler_with_isolated_env._handle_task("test prompt")

        handler_with_isolated_env._task_queue.add_task.assert_called_once_with("test prompt")

    def test_handle_task_empty_skipped(self, handler_with_isolated_env):
        """Test _handle_task skips empty prompt"""
        handler_with_isolated_env._task_queue = MagicMock()
        handler_with_isolated_env._handle_task("")
        handler_with_isolated_env._task_queue.add_task.assert_not_called()

    def test_handle_help_outputs_text(self, handler_with_isolated_env, capsys):
        """Test _handle_help prints help text"""
        handler_with_isolated_env._handle_help()
        captured = capsys.readouterr()
        assert "/task" in captured.out
        assert "/help" in captured.out
        assert "/quit" in captured.out

    def test_shutdown_stops_handler(self, handler_with_isolated_env):
        """Test _shutdown sets running to False"""
        assert handler_with_isolated_env.running is True
        handler_with_isolated_env._shutdown()
        assert handler_with_isolated_env.running is False

    def test_handler_creates_own_queue(self):
        """Test FifoInputHandler creates its own TaskQueue internally"""
        with patch.dict(os.environ, {}, clear=True):
            handler = FifoInputHandler()
            # Should have a TaskQueue instance, not None
            from swarm.task_queue import TaskQueue
            assert isinstance(handler._task_queue, TaskQueue)


class TestFifoCreation:
    """Tests for FIFO creation"""

    def test_ensure_fifo_creates_fifo(self, tmp_path):
        """Test _ensure_fifo_exists creates a FIFO"""
        with patch.dict(os.environ, {"AI_SWARM_DIR": str(tmp_path)}):
            handler = FifoInputHandler()
            # Handler uses get_fifo_path() which respects env
            assert os.path.basename(handler.fifo_path) == "master_inbox"
            handler._ensure_fifo_exists()
            assert stat.S_ISFIFO(os.lstat(handler.fifo_path).st_mode)


class TestBroadcastSignature:
    """Tests for broadcast_start() signature (no worker_id parameter)"""

    def test_broadcast_start_signature_no_worker_id(self):
        """Test broadcast_start is called with task_id and message only"""
        with patch.dict(os.environ, {}, clear=True):
            handler = FifoInputHandler()
            handler._broadcaster = MagicMock()

            handler._handle_task("test prompt")

            # broadcast_start should be called with task_id and message
            # Signature: broadcast_start(task_id, message, meta=None)
            handler._broadcaster.broadcast_start.assert_called_once()
            call_args = handler._broadcaster.broadcast_start.call_args

            # call_args is (args, kwargs)
            args, kwargs = call_args

            # Should have task_id and message in kwargs
            assert 'task_id' in kwargs
            assert 'message' in kwargs
            # Should NOT have worker_id
            assert 'worker_id' not in kwargs


class TestNonBlockingWrite:
    """Tests for write_to_fifo_nonblocking function"""

    def test_write_to_fifo_nonblocking_success(self, tmp_path):
        """Test successful non-blocking write to FIFO"""
        fifo_path = str(tmp_path / "test_fifo")
        os.mkfifo(fifo_path, mode=0o666)

        # Start a reader in background (to prevent ENXIO)
        import subprocess
        reader = subprocess.Popen(['cat', fifo_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.1)  # Give reader time to open

        try:
            from swarm.fifo_input import write_to_fifo_nonblocking
            result = write_to_fifo_nonblocking(fifo_path, "test message")
            assert result is True
        finally:
            reader.terminate()
            reader.wait()

    def test_write_to_fifo_nonblocking_no_reader(self, tmp_path):
        """Test write returns False when no reader"""
        fifo_path = str(tmp_path / "test_fifo")
        os.mkfifo(fifo_path, mode=0o666)

        from swarm.fifo_input import write_to_fifo_nonblocking
        # No reader, should return False (ENXIO or EAGAIN)
        result = write_to_fifo_nonblocking(fifo_path, "test message")
        assert result is False

    def test_write_to_fifo_nonblocking_nonexistent(self, tmp_path):
        """Test write raises exception when FIFO doesn't exist"""
        fifo_path = str(tmp_path / "nonexistent_fifo")

        from swarm.fifo_input import write_to_fifo_nonblocking
        with pytest.raises(FileNotFoundError):
            write_to_fifo_nonblocking(fifo_path, "test message")


class TestThreadIndependence:
    """Tests for thread independence (Master vs FIFO handler)"""

    def test_quit_only_stops_handler(self):
        """Test /quit only stops FifoInputHandler, not Master"""
        with patch.dict(os.environ, {}, clear=True):
            handler = FifoInputHandler()
            handler._broadcaster = MagicMock()

            # Simulate /quit
            handler.running = True
            handler._shutdown()

            # Only handler.running should be False, not master
            assert handler.running is False
