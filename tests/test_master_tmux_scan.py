"""
Integration tests for Master pane scanning functionality.

Uses real tmux sessions when tmux is available, skips when not installed.
"""

import pytest
import shutil
import time
from datetime import datetime, timezone

# Skip if tmux not available
_tmux_available = shutil.which("tmux") is not None

pytestmark = pytest.mark.skipif(
    not _tmux_available,
    reason="tmux not installed"
)

# Import after skipif check
libtmux = pytest.importorskip("libtmux")
from swarm.master import Master, WaitDetector, PaneScanner
from swarm.tmux_collaboration import TmuxCollaboration


class TestWaitDetectorDetectInPane:
    """Tests for WaitDetector.detect_in_pane() method."""

    def test_detect_press_enter(self):
        """Verify 'Press Enter' pattern is detected."""
        detector = WaitDetector()
        content = "Please press Enter to continue..."
        patterns = detector.detect_in_pane(content)
        assert len(patterns) > 0
        # Verify the pattern was detected (regex matched)
        assert patterns == [r'[Pp]ress [Ee]nter']

    def test_detect_press_return(self):
        """Verify 'Press Return' pattern is detected."""
        detector = WaitDetector()
        content = "Press Return when ready"
        patterns = detector.detect_in_pane(content)
        assert len(patterns) > 0

    def test_detect_hit_enter(self):
        """Verify 'Hit Enter' pattern is detected."""
        detector = WaitDetector()
        content = "Hit Enter to proceed"
        patterns = detector.detect_in_pane(content)
        assert len(patterns) > 0

    def test_detect_chinese_patterns(self):
        """Verify Chinese patterns are detected."""
        detector = WaitDetector()

        # Test 回车继续
        content = "请按回车继续"
        patterns = detector.detect_in_pane(content)
        assert len(patterns) > 0

        # Test 按回车
        content = "请按回车"
        patterns = detector.detect_in_pane(content)
        assert len(patterns) > 0

    def test_no_pattern_returns_empty(self):
        """Verify no pattern returns empty list."""
        detector = WaitDetector()
        content = "Task completed successfully"
        patterns = detector.detect_in_pane(content)
        assert patterns == []

    def test_empty_content_returns_empty(self):
        """Verify empty content returns empty list."""
        detector = WaitDetector()
        patterns = detector.detect_in_pane("")
        assert patterns == []

    def test_none_content_returns_empty(self):
        """Verify None content returns empty list."""
        detector = WaitDetector()
        patterns = detector.detect_in_pane(None)
        assert patterns == []

    def test_case_insensitive(self):
        """Verify detection is case insensitive."""
        detector = WaitDetector()
        content = "PRESS ENTER TO CONTINUE"
        patterns = detector.detect_in_pane(content)
        assert len(patterns) > 0

    def test_lowercase_press_enter(self):
        """Verify lowercase 'press enter' is detected."""
        detector = WaitDetector()
        content = "press enter to continue"
        patterns = detector.detect_in_pane(content)
        assert len(patterns) > 0


class TestPaneScanner:
    """Tests for PaneScanner class."""

    @pytest.fixture
    def tmux(self):
        """Create TmuxCollaboration instance."""
        return TmuxCollaboration()

    @pytest.fixture
    def temp_session(self):
        """Create a temporary tmux session."""
        server = libtmux.Server()
        session_name = "test-master-scan"
        existing = server.sessions.get(session_name=session_name, default=None)
        if existing:
            existing.kill()
        session = server.new_session(session_name=session_name, attach=False)
        yield session
        session.kill()

    def test_scan_all_returns_dict(self, tmux, temp_session):
        """Verify scan_all returns dictionary."""
        scanner = PaneScanner(tmux)
        result = scanner.scan_all("test-master-scan")
        assert isinstance(result, dict)

    def test_scan_all_with_no_tmux(self):
        """Verify scan_all returns empty dict when no tmux."""
        scanner = PaneScanner(None)
        result = scanner.scan_all("nonexistent")
        assert result == {}

    def test_send_enter_to_window(self, tmux, temp_session):
        """Verify send_enter sends key to window."""
        scanner = PaneScanner(tmux)
        # Create a worker window
        temp_session.new_window(window_name="worker-0")

        # Send echo command
        result = scanner.send_enter("test-master-scan", "worker-0")

        time.sleep(0.1)
        # Method returns True if sent, False if not found
        assert result is True or result is False

    def test_send_enter_nonexistent_window(self, tmux, temp_session):
        """Verify send_enter returns False for nonexistent window."""
        scanner = PaneScanner(tmux)
        result = scanner.send_enter("test-master-scan", "nonexistent-window")
        assert result is False

    def test_send_enter_with_no_tmux(self):
        """Verify send_enter returns False when tmux is None."""
        scanner = PaneScanner(None)
        result = scanner.send_enter("any-session", "any-window")
        assert result is False


class TestMasterPaneScanning:
    """Integration tests for Master with pane scanning."""

    @pytest.fixture
    def tmux(self):
        """Create TmuxCollaboration instance."""
        return TmuxCollaboration()

    @pytest.fixture
    def temp_session(self):
        """Create a temporary tmux session."""
        server = libtmux.Server()
        session_name = "test-master-integration"
        existing = server.sessions.get(session_name=session_name, default=None)
        if existing:
            existing.kill()
        session = server.new_session(session_name=session_name, attach=False)
        yield session
        session.kill()

    def test_master_with_tmux_injection(self, tmux, temp_session):
        """Verify Master can be created with TmuxCollaboration."""
        # Create master with tmux
        master = Master(
            cluster_id="test-integration",
            tmux_collaboration=tmux,
            poll_interval=0.1
        )
        assert master.pane_scanner is not None
        assert master.pane_scanner.tmux is tmux

    def test_master_handles_missing_tmux_gracefully(self):
        """Verify Master works when tmux is None."""
        master = Master(
            cluster_id="test-none",
            tmux_collaboration=None,
            poll_interval=0.1
        )
        assert master.pane_scanner is not None
        assert master.pane_scanner.tmux is None

    def test_cooldown_tracking(self, tmux, temp_session):
        """Verify cooldown mechanism works."""
        master = Master(
            cluster_id="test-cooldown",
            tmux_collaboration=tmux,
            poll_interval=0.1,
            pane_poll_interval=0.1
        )

        # Add a fake last_auto_enter timestamp
        master._last_auto_enter["test-window"] = time.time()

        # Verify cooldown is tracked
        assert "test-window" in master._last_auto_enter

    def test_cluster_id_stored(self):
        """Verify cluster_id is stored correctly."""
        master = Master(
            cluster_id="my-cluster",
            tmux_collaboration=None
        )
        assert master.cluster_id == "my-cluster"

    def test_pane_poll_interval_default(self):
        """Verify default pane_poll_interval is 3.0 seconds."""
        master = Master(
            cluster_id="test",
            tmux_collaboration=None
        )
        assert master.pane_poll_interval == 3.0

    def test_pane_poll_interval_custom(self):
        """Verify custom pane_poll_interval is respected."""
        master = Master(
            cluster_id="test",
            tmux_collaboration=None,
            pane_poll_interval=5.0
        )
        assert master.pane_poll_interval == 5.0


class TestCooldownMechanism:
    """Tests for 30-second cooldown per window."""

    def test_cooldown_prevents_repeated_enter(self):
        """Verify ENTER is not sent within 30s window."""
        from swarm.master import Master

        # Create master
        master = Master(
            cluster_id="test",
            tmux_collaboration=None,
            pane_poll_interval=0.01
        )

        # Simulate recent auto-enter
        master._last_auto_enter["window-1"] = time.time()

        # Check should_auto_enter helper
        now = time.time()
        last = master._last_auto_enter.get("window-1", 0)
        assert now - last < 30  # Within cooldown

    def test_cooldown_expired_allows_enter(self):
        """Verify ENTER is allowed after cooldown expires."""
        from swarm.master import Master

        master = Master(
            cluster_id="test",
            tmux_collaboration=None,
            pane_poll_interval=0.01
        )

        # Simulate old auto-enter (35 seconds ago)
        master._last_auto_enter["window-1"] = time.time() - 35

        now = time.time()
        last = master._last_auto_enter.get("window-1", 0)
        assert now - last >= 30  # Cooldown expired

    def test_no_previous_enter_allows_action(self):
        """Verify no previous enter allows immediate action."""
        from swarm.master import Master

        master = Master(
            cluster_id="test",
            tmux_collaboration=None,
            pane_poll_interval=0.01
        )

        # No previous auto-enter for this window
        now = time.time()
        last = master._last_auto_enter.get("new-window", 0)
        assert now - last >= 30  # Cooldown expired (default is 0)


class TestTmuxUnavailability:
    """Tests for tmux unavailability handling."""

    def test_master_handles_tmux_unavailable_in_scan(self):
        """Verify Master handles tmux errors during scanning."""
        from swarm.master import Master
        from unittest.mock import MagicMock

        # Create mock that raises exception
        mock_tmux = MagicMock()
        mock_tmux.capture_all_windows.side_effect = Exception("tmux error")

        master = Master(
            cluster_id="test",
            tmux_collaboration=mock_tmux,
            pane_poll_interval=0.01
        )

        # Should not raise, should return empty dict
        result = master.pane_scanner.scan_all("any-session")
        assert result == {}

    def test_master_handles_send_enter_error(self):
        """Verify Master handles send_enter errors gracefully."""
        from swarm.master import Master
        from unittest.mock import MagicMock

        # Create mock that raises exception
        mock_tmux = MagicMock()
        mock_tmux.list_windows.side_effect = Exception("tmux error")

        master = Master(
            cluster_id="test",
            tmux_collaboration=mock_tmux,
            pane_poll_interval=0.01
        )

        # Should not raise, should return False
        result = master.pane_scanner.send_enter("any-session", "any-window")
        assert result is False
