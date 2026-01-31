"""
E2E test for CLI command verification (no task execution)

Purpose: Verify swarm CLI commands work with real tmux sessions.
This test verifies: swarm up -> status -> down

Run with: pytest tests/test_e2e_happy_path.py -v -m integration
"""

import pytest
import subprocess
import sys
import time
import os
import json
import uuid
import shutil


# Module-level marker for integration tests
pytestmark = pytest.mark.integration


def check_tmux_available():
    """Check if tmux is installed and available."""
    return shutil.which('tmux') is not None


# Skip the entire module if tmux is not available
pytestmark = pytest.mark.skipif(
    not check_tmux_available(),
    reason="tmux not installed - skipping integration test"
)


@pytest.fixture
def unique_cluster_id():
    """Generate unique cluster ID for tmux session naming."""
    return f"test-happy-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def isolated_swarm_dir(tmp_path, unique_cluster_id):
    """Create isolated AI_SWARM_DIR for this test."""
    swarm_dir = tmp_path / "ai_swarm" / unique_cluster_id
    swarm_dir.mkdir(parents=True, exist_ok=True)
    return str(swarm_dir)


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
        shutil.rmtree(swarm_dir)


def session_exists(cluster_id):
    """Check if tmux session exists for the given cluster."""
    result = subprocess.run(
        ['tmux', 'has-session', '-t', f'swarm-{cluster_id}'],
        capture_output=True
    )
    return result.returncode == 0


def count_windows(cluster_id):
    """
    Count windows in tmux session (master + workers).

    Returns the number of windows in the swarm cluster session.
    """
    result = subprocess.run(
        ['tmux', 'list-windows', '-t', f'swarm-{cluster_id}'],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        return 0
    # Count lines (each window is one line, minus header if present)
    lines = [l for l in result.stdout.strip().split('\n') if l]
    return len(lines)


def test_cli_commands_work(unique_cluster_id, isolated_swarm_dir):
    """
    E2E test: Verify swarm CLI commands work with real tmux.

    This test verifies:
    1. swarm up creates tmux session with master + N workers
    2. swarm status displays session and window information
    3. swarm down terminates all sessions

    Note: This test does NOT execute real LLM tasks (no API key needed).
    It only verifies the CLI commands and tmux session lifecycle.
    """
    session_name = f"swarm-{unique_cluster_id}"
    workers = 2

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

        # Verify tmux session was created
        assert session_exists(unique_cluster_id), \
            f"Session {session_name} not found after swarm up"

        # Verify windows: master + N workers
        window_count = count_windows(unique_cluster_id)
        assert window_count >= workers + 1, \
            f"Expected {workers + 1} windows (master + {workers} workers), got {window_count}"

        # Verify specific windows exist by listing them
        windows_output = subprocess.run(
            ['tmux', 'list-windows', '-t', session_name],
            capture_output=True,
            text=True
        )
        assert windows_output.returncode == 0, \
            f"Failed to list windows: {windows_output.stderr}"

        # Check for master window
        assert 'master' in windows_output.stdout, \
            f"master window not found in session: {windows_output.stdout}"

        # Check for worker windows
        for i in range(workers):
            assert f'worker-{i}' in windows_output.stdout, \
                f"worker-{i} window not found in session: {windows_output.stdout}"

        # === STEP 2: swarm status ===
        result = run_swarm_command(unique_cluster_id, 'status', [], isolated_swarm_dir)

        assert result.returncode == 0, \
            f"swarm status failed with code {result.returncode}: {result.stderr}"

        # Status output should contain session name and window info
        assert session_name in result.stdout or 'master' in result.stdout, \
            f"Status output missing session info. Got: {result.stdout}"

        # === STEP 3: swarm down ===
        result = run_swarm_command(unique_cluster_id, 'down', [], isolated_swarm_dir)

        assert result.returncode == 0, \
            f"swarm down failed with code {result.returncode}: {result.stderr}"

        # Verify session was terminated
        assert not session_exists(unique_cluster_id), \
            f"Session {session_name} still exists after swarm down"

    finally:
        # Always cleanup to avoid leaving sessions
        cleanup_cluster(unique_cluster_id, isolated_swarm_dir)
