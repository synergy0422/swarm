#!/usr/bin/env python3
"""
Regression tests for MVP constraints.

Ensures:
1. No hardcoded legacy paths like ~/group/ai_swarm (in source code, not tests)
2. AI_SWARM_DIR environment variable takes precedence
3. Default path is /tmp/ai_swarm
"""

import os
import subprocess
import pytest


class TestNoLegacyPaths:
    """Ensure no hardcoded legacy paths exist in source code."""

    def test_no_hardcoded_group_ai_swarm_in_source(self):
        """
        Regression test: ~/group/ai_swarm should not exist in source files.

        This was the original hardcoded path that caused MVP constraint violation.
        All paths should now use AI_SWARM_DIR env var with /tmp/ai_swarm default.

        Note: Tests directory is excluded to avoid matching this test itself.
        """
        # Search swarm/ directory for the legacy path pattern
        result = subprocess.run(
            ['grep', '-R', '~/group/ai_swarm',
             '--include=*.py',
             'swarm/'],
            capture_output=True,
            text=True,
            cwd='/home/user/AAA/swarm'
        )

        # Also check root-level Python files
        root_result = subprocess.run(
            ['grep', '-R', '~/group/ai_swarm',
             '--include=*.py',
             '--exclude-dir=tests',
             '--exclude=*.pyc'],
            capture_output=True,
            text=True,
            cwd='/home/user/AAA/swarm'
        )

        # grep returns exit code 1 when no matches found (which is what we want)
        combined_output = result.stdout + root_result.stdout
        assert result.returncode == 1 and root_result.returncode == 1, (
            f"Found hardcoded ~/group/ai_swarm paths (MVP violation):\n"
            f"{combined_output}"
        )

    def test_no_dotenv_loading_in_source(self):
        """
        Regression test: No dotenv or load_dotenv should exist in source code.

        API keys must only come from environment variables, not from .env files.

        Note: Tests directory is excluded to avoid matching this test itself.
        """
        result = subprocess.run(
            ['grep', '-R', r'dotenv\|load_dotenv',
             '--include=*.py',
             'swarm/'],
            capture_output=True,
            text=True,
            cwd='/home/user/AAA/swarm'
        )

        # Also check root-level Python files
        root_result = subprocess.run(
            ['grep', '-R', r'dotenv\|load_dotenv',
             '--include=*.py',
             '--exclude-dir=tests'],
            capture_output=True,
            text=True,
            cwd='/home/user/AAA/swarm'
        )

        combined_output = result.stdout + root_result.stdout
        assert result.returncode == 1 and root_result.returncode == 1, (
            f"Found dotenv loading (security violation):\n"
            f"{combined_output}"
        )


class TestAiSwarmDirDefault:
    """Ensure AI_SWARM_DIR follows MVP path configuration rules."""

    @pytest.fixture
    def non_existent_temp_dir(self, tmp_path):
        """Create a temporary directory path that doesn't exist yet."""
        return str(tmp_path / 'non_existent_dir')

    def test_ai_swarm_dir_env_override(self, monkeypatch, tmp_path):
        """
        When AI_SWARM_DIR is set, it should be used instead of /tmp/ai_swarm.
        """
        from swarm.task_queue import TaskQueue

        custom_dir = str(tmp_path / 'custom_ai_swarm')
        monkeypatch.setenv('AI_SWARM_DIR', custom_dir)

        # Create a TaskQueue and verify it uses the custom directory
        q = TaskQueue()
        expected_file = os.path.join(custom_dir, 'tasks.json')

        assert q.tasks_file == expected_file, (
            f"TaskQueue should use AI_SWARM_DIR ({custom_dir}), "
            f"but got {q.tasks_file}"
        )

    def test_default_is_tmp_ai_swarm(self, monkeypatch, tmp_path):
        """
        When AI_SWARM_DIR is NOT set, default should be /tmp/ai_swarm.
        """
        from swarm.task_queue import TaskQueue

        # Ensure AI_SWARM_DIR is not set
        monkeypatch.delenv('AI_SWARM_DIR', raising=False)

        q = TaskQueue()
        expected_file = '/tmp/ai_swarm/tasks.json'

        assert q.tasks_file == expected_file, (
            f"Default should be /tmp/ai_swarm, but got {q.tasks_file}"
        )

    def test_auto_create_directory(self, monkeypatch, non_existent_temp_dir):
        """
        Directory should be auto-created when TaskQueue is initialized.
        """
        from swarm.task_queue import TaskQueue

        monkeypatch.setenv('AI_SWARM_DIR', non_existent_temp_dir)

        # Directory should not exist yet
        assert not os.path.exists(non_existent_temp_dir)

        # Create TaskQueue - this should auto-create the directory
        q = TaskQueue()

        # Directory should now exist
        assert os.path.exists(non_existent_temp_dir), (
            f"Directory {non_existent_temp_dir} should be auto-created"
        )

    def test_path_join_usage(self, monkeypatch, tmp_path):
        """
        All paths should use os.path.join, not string concatenation.
        This test verifies the pattern by checking that paths are properly joined.
        """
        from swarm.task_queue import TaskQueue

        custom_dir = str(tmp_path / 'path_join_test')
        monkeypatch.setenv('AI_SWARM_DIR', custom_dir)

        q = TaskQueue()

        # Verify the path ends with tasks.json (properly joined)
        assert q.tasks_file.endswith('tasks.json'), (
            f"Path should end with 'tasks.json' when using os.path.join, "
            f"got {q.tasks_file}"
        )

        # Verify no double slashes or path traversal issues
        assert '//' not in q.tasks_file.replace('://', ''), (
            f"Path should not have double slashes: {q.tasks_file}"
        )


class TestWrapperNoLogic:
    """Ensure root wrapper modules contain no logic, only re-exports."""

    def test_root_task_queue_is_wrapper(self):
        """Root task_queue.py should only import from swarm.task_queue."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "task_queue", "/home/user/AAA/swarm/task_queue.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Should have __all__ defined
        assert hasattr(module, '__all__')

        # Should have minimal imports (only from swarm)
        import ast
        with open('/home/user/AAA/swarm/task_queue.py') as f:
            tree = ast.parse(f.read())

        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        # All imports should be from swarm package
        for imp in imports:
            assert imp.startswith('swarm'), (
                f"Root wrapper should only import from swarm, got: {imp}"
            )

    def test_root_worker_smart_is_wrapper(self):
        """Root worker_smart.py should only import from swarm.worker_smart."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "worker_smart", "/home/user/AAA/swarm/worker_smart.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Should have __all__ defined
        assert hasattr(module, '__all__')

        import ast
        with open('/home/user/AAA/swarm/worker_smart.py') as f:
            tree = ast.parse(f.read())

        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        # All imports should be from swarm package
        for imp in imports:
            assert imp.startswith('swarm'), (
                f"Root wrapper should only import from swarm, got: {imp}"
            )
