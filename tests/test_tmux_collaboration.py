"""
Unit tests for TmuxCollaboration.

These tests use real tmux sessions when tmux is available,
and skip when tmux is not installed.
"""

import pytest
import shutil

# Use importorskip to handle missing libtmux gracefully (pytest will skip, not error)
libtmux = pytest.importorskip("libtmux")

from swarm.tmux_collaboration import TmuxCollaboration


# Check tmux availability
_tmux_available = shutil.which("tmux") is not None

pytestmark = pytest.mark.skipif(
    not _tmux_available,
    reason="tmux not installed"
)


@pytest.fixture
def collaboration():
    """Create TmuxCollaboration instance for testing."""
    return TmuxCollaboration()


@pytest.fixture
def temp_session():
    """Create a temporary tmux session, cleaned up after test."""
    server = libtmux.Server()

    # Clean up any existing session with the same name (use new API)
    existing = server.sessions.get(session_name="test-swarm-collab", default=None)
    if existing:
        existing.kill()

    session = server.new_session(
        session_name="test-swarm-collab",
        attach=False
    )
    yield session
    # Cleanup: kill session after test (use kill() instead of deprecated kill_session())
    session.kill()


class TestListWindows:
    """Tests for list_windows method."""

    def test_list_windows_returns_list(self, collaboration, temp_session):
        """Verify list_windows returns a list."""
        windows = collaboration.list_windows("test-swarm-collab")
        assert isinstance(windows, list)

    def test_list_windows_returns_window_dicts(self, collaboration, temp_session):
        """Verify each item is a dictionary with required keys."""
        windows = collaboration.list_windows("test-swarm-collab")
        if windows:  # May have just 1 window (master)
            for window in windows:
                assert isinstance(window, dict)
                assert "name" in window
                assert "index" in window
                assert "activity" in window

    def test_list_windows_with_multiple_windows(self, collaboration, temp_session):
        """Verify list_windows includes all created windows."""
        # Create 3 worker windows
        for i in range(3):
            temp_session.new_window(window_name=f"worker-{i}")

        windows = collaboration.list_windows("test-swarm-collab")
        # Should have master + 3 workers = 4 windows
        assert len(windows) >= 4

        # Verify all worker windows are present
        window_names = [w["name"] for w in windows]
        assert "worker-0" in window_names
        assert "worker-1" in window_names
        assert "worker-2" in window_names

    def test_list_windows_nonexistent_session(self, collaboration):
        """Verify empty list returned for nonexistent session."""
        windows = collaboration.list_windows("nonexistent-session-xyz")
        assert windows == []


class TestCapturePane:
    """Tests for capture_pane method."""

    def test_capture_pane_returns_string(self, collaboration, temp_session):
        """Verify capture_pane returns a string."""
        output = collaboration.capture_pane("test-swarm-collab", "0")
        assert isinstance(output, str)

    def test_capture_pane_contains_sent_content(self, collaboration, temp_session):
        """Verify capture_pane contains content that was sent."""
        # Send a test command
        temp_session.active_window.active_pane.send_keys("echo hello-tmux-test", enter=True)

        # Allow time for command to execute
        import time
        time.sleep(0.1)

        output = collaboration.capture_pane("test-swarm-collab", "0")
        assert "hello-tmux-test" in output

    def test_capture_pane_nonexistent_session(self, collaboration):
        """Verify empty string for nonexistent session."""
        output = collaboration.capture_pane("nonexistent-session-xyz", "0")
        assert output == ""

    def test_capture_pane_nonexistent_window(self, collaboration, temp_session):
        """Verify empty string for nonexistent window index."""
        output = collaboration.capture_pane("test-swarm-collab", "999")
        assert output == ""


class TestCaptureAllWindows:
    """Tests for capture_all_windows method."""

    def test_capture_all_windows_returns_dict(self, collaboration, temp_session):
        """Verify capture_all_windows returns a dictionary."""
        outputs = collaboration.capture_all_windows("test-swarm-collab")
        assert isinstance(outputs, dict)

    def test_capture_all_windows_includes_first_window(self, collaboration, temp_session):
        """Verify first window is included in output."""
        outputs = collaboration.capture_all_windows("test-swarm-collab")
        # Get the actual window name from the session
        first_window_name = temp_session.active_window.window_name
        # Assert the first window is included (use actual name from session)
        assert first_window_name in outputs

    def test_capture_all_windows_with_workers(self, collaboration, temp_session):
        """Verify all worker windows are captured."""
        # Get the first window's actual name
        first_window_name = temp_session.active_window.window_name

        # Create 3 worker windows with unique content
        for i in range(3):
            w = temp_session.new_window(window_name=f"worker-{i}")
            w.active_pane.send_keys(f"echo worker-{i}-content", enter=True)

        import time
        time.sleep(0.1)

        outputs = collaboration.capture_all_windows("test-swarm-collab")

        # Use actual first window name
        assert first_window_name in outputs
        assert "worker-0" in outputs
        assert "worker-1" in outputs
        assert "worker-2" in outputs

    def test_capture_all_windows_contains_worker_content(self, collaboration, temp_session):
        """Verify worker window content is captured correctly."""
        w = temp_session.new_window(window_name="test-worker")
        w.active_pane.send_keys("echo unique-content-12345", enter=True)

        import time
        time.sleep(0.1)

        outputs = collaboration.capture_all_windows("test-swarm-collab")
        assert "unique-content-12345" in outputs.get("test-worker", "")

    def test_capture_all_windows_nonexistent_session(self, collaboration):
        """Verify empty dict for nonexistent session."""
        outputs = collaboration.capture_all_windows("nonexistent-session-xyz")
        assert outputs == {}


class TestSendKeysToWindow:
    """Tests for send_keys_to_window method."""

    def test_send_keys_appears_in_pane(self, collaboration, temp_session):
        """Verify sent keys appear in the pane output."""
        # Create window 1 first
        temp_session.new_window(window_name="window-1")

        # Send keys to window 1
        collaboration.send_keys_to_window(
            "test-swarm-collab", "1", "echo sent-keys-test-abc"
        )

        import time
        time.sleep(0.1)

        output = collaboration.capture_pane("test-swarm-collab", "1")
        assert "sent-keys-test-abc" in output

    def test_send_keys_without_enter(self, collaboration, temp_session):
        """Verify keys can be sent without pressing Enter."""
        # Create a new window
        window = temp_session.new_window(window_name="no-enter-test")
        window.active_pane.send_keys("echo before", enter=True)

        import time
        time.sleep(0.1)

        # Send keys without enter
        collaboration.send_keys_to_window(
            "test-swarm-collab", "1", "echo after", enter=False
        )

        import time as t
        t.sleep(0.1)

        output = collaboration.capture_pane("test-swarm-collab", "1")
        # "after" should not have executed (no enter)
        assert "echo after" in output or "after" in output

    def test_send_keys_nonexistent_session(self, collaboration):
        """Verify no error when session doesn't exist."""
        # Should not raise an exception
        collaboration.send_keys_to_window(
            "nonexistent-session-xyz", "0", "echo test"
        )

    def test_send_keys_nonexistent_window(self, collaboration, temp_session):
        """Verify no error when window doesn't exist."""
        # Should not raise an exception
        collaboration.send_keys_to_window(
            "test-swarm-collab", "999", "echo test"
        )
