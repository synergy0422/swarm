"""
Unit tests for --panes flag in swarm status command.

Tests the format_pane_output() function and --panes flag handling.

Unit tests (TestStatusIconDetection, TestTwentyLineLimit, etc.) run without tmux.
Integration tests (test_status_panes_flag) require both tmux and libtmux.
"""

import pytest
from swarm.cli import format_pane_output


# Unit tests - no tmux dependency
pytestmark = pytest.mark.unit


class TestStatusIconDetection:
    """Tests for status icon detection in pane content."""

    def test_status_icon_error_for_error(self):
        """Verify [ERROR] icon when content contains 'Error'."""
        pane_contents = {
            "master": "Task failed: Error processing request",
            "worker-0": "",
            "worker-1": "",
            "worker-2": ""
        }
        result = format_pane_output(pane_contents)
        assert "=== master [ERROR] ===" in result

    def test_status_icon_error_for_failed(self):
        """Verify [ERROR] icon when content contains 'Failed'."""
        pane_contents = {
            "master": "Operation Failed due to timeout",
            "worker-0": "",
            "worker-1": "",
            "worker-2": ""
        }
        result = format_pane_output(pane_contents)
        assert "=== master [ERROR] ===" in result

    def test_status_icon_error_case_insensitive(self):
        """Verify [ERROR] icon detection is case-insensitive."""
        pane_contents = {
            "master": "ERROR: Something went wrong",
            "worker-0": "",
            "worker-1": "",
            "worker-2": ""
        }
        result = format_pane_output(pane_contents)
        assert "=== master [ERROR] ===" in result

    def test_status_icon_done_for_done(self):
        """Verify [DONE] icon when content contains 'DONE'."""
        pane_contents = {
            "master": "Task DONE successfully",
            "worker-0": "",
            "worker-1": "",
            "worker-2": ""
        }
        result = format_pane_output(pane_contents)
        assert "=== master [DONE] ===" in result

    def test_status_icon_done_for_complete(self):
        """Verify [DONE] icon when content contains 'Complete'."""
        pane_contents = {
            "master": "Operation Complete",
            "worker-0": "",
            "worker-1": "",
            "worker-2": ""
        }
        result = format_pane_output(pane_contents)
        assert "=== master [DONE] ===" in result

    def test_status_icon_done_case_insensitive(self):
        """Verify [DONE] icon detection is case-insensitive."""
        pane_contents = {
            "master": "complete: all tasks finished",
            "worker-0": "",
            "worker-1": "",
            "worker-2": ""
        }
        result = format_pane_output(pane_contents)
        assert "=== master [DONE] ===" in result

    def test_status_icon_neutral_for_no_match(self):
        """Verify [ ] icon when content has no error/done keywords."""
        pane_contents = {
            "master": "Processing task 123...",
            "worker-0": "",
            "worker-1": "",
            "worker-2": ""
        }
        result = format_pane_output(pane_contents)
        assert "=== master [ ] ===" in result

    def test_status_icon_neutral_for_empty_content(self):
        """Verify [ ] icon for empty content (missing window)."""
        pane_contents = {
            "master": "",
            "worker-0": "",
            "worker-1": "",
            "worker-2": ""
        }
        result = format_pane_output(pane_contents)
        assert "=== master [ ] ===" in result


class TestTwentyLineLimit:
    """Tests for 20-line content limit."""

    def test_20_line_limit(self):
        """Verify only last 20 lines are shown."""
        # Create content with 30 lines
        lines = [f"Line {i}" for i in range(1, 31)]
        pane_contents = {
            "master": '\n'.join(lines),
            "worker-0": "",
            "worker-1": "",
            "worker-2": ""
        }
        result = format_pane_output(pane_contents)
        # Should contain Line 11-30 (last 20 lines)
        assert "Line 11" in result
        assert "Line 30" in result
        # Should NOT contain Line 10 or earlier (check for exact line numbers)
        assert "Line 10\n" not in result
        assert "Line 9\n" not in result
        assert "Line 1\n" not in result

    def test_less_than_20_lines_no_truncation(self):
        """Verify content with <20 lines is not truncated."""
        pane_contents = {
            "master": "Line 1\nLine 2\nLine 3",
            "worker-0": "",
            "worker-1": "",
            "worker-2": ""
        }
        result = format_pane_output(pane_contents)
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result


class TestMissingWindowDisplay:
    """Tests for missing window handling."""

    def test_missing_window_shows_placeholder(self):
        """Verify (missing) is shown for windows without content."""
        pane_contents = {
            "master": "Master is running",
            # worker-0, worker-1, worker-2 are missing
        }
        result = format_pane_output(pane_contents)
        assert "=== worker-0 [ ] ===" in result
        assert "(missing)" in result
        assert "=== worker-1 [ ] ===" in result
        assert "(missing)" in result
        assert "=== worker-2 [ ] ===" in result
        assert "(missing)" in result

    def test_all_windows_missing(self):
        """Verify behavior when all windows are missing."""
        pane_contents = {}
        result = format_pane_output(pane_contents)
        assert "=== master [ ] ===" in result
        assert "(missing)" in result
        assert "=== worker-0 [ ] ===" in result
        assert "(missing)" in result


class TestWindowOrder:
    """Tests for window display order."""

    def test_window_order_master_first(self):
        """Verify master window appears first."""
        pane_contents = {
            "master": "master content",
            "worker-0": "worker-0 content",
            "worker-1": "worker-1 content",
            "worker-2": "worker-2 content"
        }
        result = format_pane_output(pane_contents)
        master_idx = result.index("=== master")
        worker0_idx = result.index("=== worker-0")
        worker1_idx = result.index("=== worker-1")
        worker2_idx = result.index("=== worker-2")
        assert master_idx < worker0_idx < worker1_idx < worker2_idx

    def test_extra_windows_filtered(self):
        """Verify extra windows not in required list are filtered out."""
        pane_contents = {
            "master": "master content",
            "worker-0": "worker-0 content",
            "worker-1": "worker-1 content",
            "worker-2": "worker-2 content",
            "debug-0": "debug content",  # Extra window
            "monitor": "monitor content"  # Extra window
        }
        result = format_pane_output(pane_contents)
        assert "=== debug-0 ===" not in result
        assert "=== monitor ===" not in result
        # Required windows should still be present (with status icon)
        assert "=== master [ ] ===" in result
        assert "=== worker-0 [ ] ===" in result
        assert "=== worker-1 [ ] ===" in result
        assert "=== worker-2 [ ] ===" in result


# Integration tests for --panes flag (require tmux and libtmux)
import sys
import os
import uuid
import shutil
import subprocess

# Integration tests require tmux and libtmux
_tmux_available = shutil.which('tmux') is not None
pytestmark_integration = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _tmux_available,
        reason="tmux not installed"
    )
]


def run_swarm_command(cluster_id, command, args, swarm_dir):
    """
    Run swarm CLI with isolated AI_SWARM_DIR.

    Args:
        cluster_id: The cluster identifier
        command: CLI subcommand (up, status, down, etc.)
        args: Additional arguments for the command
        swarm_dir: Isolated AI_SWARM_DIR path

    Returns:
        subprocess.CompletedProcess with stdout/stderr
    """
    cmd = [
        sys.executable, '-m', 'swarm.cli',
        command,
        '--cluster-id', cluster_id
    ] + args

    env = os.environ.copy()
    env['AI_SWARM_DIR'] = swarm_dir

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env
    )
    return result


def cleanup_cluster(cluster_id, swarm_dir):
    """Cleanup tmux session and files."""
    # Kill the tmux session
    subprocess.run(
        ['tmux', 'kill-session', '-t', f'swarm-{cluster_id}'],
        capture_output=True
    )

    # Remove the isolated swarm directory
    if os.path.exists(swarm_dir):
        import shutil
        shutil.rmtree(swarm_dir)


def session_exists(cluster_id):
    """Check if tmux session exists for the given cluster."""
    result = subprocess.run(
        ['tmux', 'has-session', '-t', f'swarm-{cluster_id}'],
        capture_output=True
    )
    return result.returncode == 0


@pytest.fixture
def unique_cluster_id():
    """Generate unique cluster ID for tmux session naming."""
    return f"test-panes-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def isolated_swarm_dir(tmp_path, unique_cluster_id):
    """Create isolated AI_SWARM_DIR for this test."""
    swarm_dir = tmp_path / "ai_swarm" / unique_cluster_id
    swarm_dir.mkdir(parents=True, exist_ok=True)
    return str(swarm_dir)


@pytest.mark.integration
def test_status_panes_flag(unique_cluster_id, isolated_swarm_dir):
    """
    Integration test: Verify --panes flag works end-to-end.

    This test verifies:
    1. swarm status --panes displays pane snapshots when session exists
    2. swarm status (without --panes) does not display pane snapshots
    3. swarm status --panes works gracefully when session doesn't exist
    """
    # Skip if libtmux is not available
    pytest.importorskip("libtmux")

    workers = 2
    session_name = f"swarm-{unique_cluster_id}"

    try:
        # === STEP 1: swarm up ===
        result = run_swarm_command(
            unique_cluster_id,
            'up',
            ['--workers', str(workers)],
            isolated_swarm_dir
        )

        assert result.returncode == 0, \
            f"swarm up failed with code {result.returncode}: {result.stderr}"
        assert session_exists(unique_cluster_id), \
            f"Session {session_name} not found after swarm up"

        # === STEP 2: swarm status --panes ===
        result = run_swarm_command(unique_cluster_id, 'status', ['--panes'], isolated_swarm_dir)

        assert result.returncode == 0, \
            f"swarm status --panes failed with code {result.returncode}: {result.stderr}"

        # Output should contain pane sections
        assert "=== master" in result.stdout, \
            f"Pane output missing master window. Got: {result.stdout[:500]}"
        assert "=== worker-0" in result.stdout, \
            f"Pane output missing worker-0 window. Got: {result.stdout[:500]}"

        # === STEP 3: swarm status (without --panes) ===
        result = run_swarm_command(unique_cluster_id, 'status', [], isolated_swarm_dir)

        assert result.returncode == 0, \
            f"swarm status failed with code {result.returncode}: {result.stderr}"

        # Output should NOT contain pane sections
        assert "=== master" not in result.stdout, \
            f"Status without --panes should not show pane output. Got: {result.stdout[:500]}"
        assert "=== worker-0" not in result.stdout, \
            f"Status without --panes should not show pane output. Got: {result.stdout[:500]}"

        # === STEP 4: swarm status --panes (no session) ===
        # First, bring down the session
        run_swarm_command(unique_cluster_id, 'down', [], isolated_swarm_dir)

        # Now test --panes with no session (should skip panes gracefully)
        result = run_swarm_command(unique_cluster_id, 'status', ['--panes'], isolated_swarm_dir)

        assert result.returncode == 0, \
            f"swarm status --panes should return 0 even without session. Got: {result.returncode}"

    finally:
        # Always cleanup to avoid leaving sessions
        cleanup_cluster(unique_cluster_id, isolated_swarm_dir)
