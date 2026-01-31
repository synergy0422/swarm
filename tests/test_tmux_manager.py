"""
Unit tests for TmuxSwarmManager.

Tests use mocked tmux operations for isolation.
"""

import pytest
from unittest.mock import MagicMock, patch
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock libtmux before any swarm imports (libtmux is not installed in test env)
_mock_libtmux = MagicMock()
sys.modules['libtmux'] = _mock_libtmux


class TestAgentStatus:
    """Tests for AgentStatus enum."""

    def test_agent_status_values(self):
        """Verify all expected status values exist."""
        # Mock libtmux before importing
        with patch.dict('sys.modules', {'libtmux': MagicMock()}):
            from swarm.tmux_manager import AgentStatus

            assert AgentStatus.PENDING.value == "pending"
            assert AgentStatus.RUNNING.value == "running"
            assert AgentStatus.STOPPED.value == "stopped"
            assert AgentStatus.FAILED.value == "failed"
            assert AgentStatus.UNKNOWN.value == "unknown"

    def test_agent_status_count(self):
        """Verify exactly 5 status values."""
        with patch.dict('sys.modules', {'libtmux': MagicMock()}):
            from swarm.tmux_manager import AgentStatus

            assert len(AgentStatus) == 5


class TestAgentPane:
    """Tests for AgentPane dataclass."""

    def test_agent_pane_creation(self):
        """Verify AgentPane can be created with required fields."""
        with patch.dict('sys.modules', {'libtmux': MagicMock()}):
            from swarm.tmux_manager import AgentPane, AgentStatus

            mock_pane = MagicMock()
            pane = AgentPane(
                agent_id="agent-1",
                pane_id="%1",
                window_id="@1",
                session_id="$1",
                pane=mock_pane,
                status=AgentStatus.RUNNING
            )

            assert pane.agent_id == "agent-1"
            assert pane.pane_id == "%1"
            assert pane.window_id == "@1"
            assert pane.session_id == "$1"
            assert pane.pane is mock_pane
            assert pane.status == AgentStatus.RUNNING

    def test_agent_pane_default_status(self):
        """Verify default status is PENDING."""
        with patch.dict('sys.modules', {'libtmux': MagicMock()}):
            from swarm.tmux_manager import AgentPane, AgentStatus

            mock_pane = MagicMock()
            pane = AgentPane(
                agent_id="agent-1",
                pane_id="%1",
                window_id="@1",
                session_id="$1",
                pane=mock_pane
            )

            assert pane.status == AgentStatus.PENDING


class TestTmuxSwarmManagerInit:
    """Tests for TmuxSwarmManager initialization."""

    def test_initialization_defaults(self, isolated_swarm_dir):
        """Verify manager initializes with correct defaults."""
        with patch.dict('sys.modules', {'libtmux': MagicMock()}):
            from swarm.tmux_manager import TmuxSwarmManager

            mgr = TmuxSwarmManager(
                cluster_id="test-cluster",
                base_dir="/home/user/AAA/swarm",
                socket_path=None
            )

            assert mgr.cluster_id == "test-cluster"
            assert mgr.base_dir == "/home/user/AAA/swarm"
            assert mgr.socket_path is None
            assert mgr._session is None
            assert mgr._agents == {}

    def test_data_dir_from_env(self, isolated_swarm_dir):
        """Verify data_dir is set from AI_SWARM_DIR env var."""
        with patch.dict('sys.modules', {'libtmux': MagicMock()}):
            from swarm.tmux_manager import TmuxSwarmManager

            mgr = TmuxSwarmManager(cluster_id="test")

            assert mgr.data_dir == isolated_swarm_dir

    def test_data_dir_default(self, monkeypatch):
        """Verify default data_dir when AI_SWARM_DIR not set."""
        monkeypatch.delenv('AI_SWARM_DIR', raising=False)

        with patch.dict('sys.modules', {'libtmux': MagicMock()}):
            from swarm.tmux_manager import TmuxSwarmManager

            mgr = TmuxSwarmManager(cluster_id="test")

            assert mgr.data_dir == "/tmp/ai_swarm/"


class TestTmuxSwarmManagerSession:
    """Tests for TmuxSwarmManager session management."""

    @pytest.fixture
    def manager(self, isolated_swarm_dir):
        """Create a TmuxSwarmManager instance."""
        with patch.dict('sys.modules', {'libtmux': MagicMock()}):
            from swarm.tmux_manager import TmuxSwarmManager

            mgr = TmuxSwarmManager(
                cluster_id="test-cluster",
                base_dir="/home/user/AAA/swarm"
            )
            yield mgr

    def test_list_agents_empty(self, manager):
        """Verify list_agents() returns empty list initially."""
        assert manager.list_agents() == []

    def test_get_session_info_inactive(self, manager):
        """Verify get_session_info() for inactive session."""
        info = manager.get_session_info()

        assert info['active'] is False

    def test_shutdown_clears_state(self, manager):
        """Verify shutdown() clears all state."""
        import asyncio

        mock_session = MagicMock()
        manager._session = mock_session
        manager._agents["agent-1"] = MagicMock()

        asyncio.run(manager.shutdown(graceful=False))

        mock_session.kill_session.assert_called_once()
        assert manager._session is None
        assert manager._agents == {}


class TestTmuxSwarmManagerAgent:
    """Tests for TmuxSwarmManager agent management."""

    @pytest.fixture
    def manager(self, isolated_swarm_dir):
        """Create a TmuxSwarmManager instance."""
        with patch.dict('sys.modules', {'libtmux': MagicMock()}):
            from swarm.tmux_manager import TmuxSwarmManager

            mgr = TmuxSwarmManager(
                cluster_id="test-cluster",
                base_dir="/home/user/AAA/swarm"
            )
            yield mgr

    def test_spawn_agent_requires_session(self, manager):
        """Verify spawn_agent() fails without active session."""
        import asyncio
        from swarm.exceptions import SessionNotFoundError

        with pytest.raises(SessionNotFoundError):
            asyncio.run(manager.spawn_agent("agent-1", "python agent.py"))

    def test_kill_agent_raises_for_missing(self, manager):
        """Verify kill_agent() raises for non-existent agent."""
        import asyncio
        from swarm.exceptions import AgentNotFoundError

        with pytest.raises(AgentNotFoundError):
            asyncio.run(manager.kill_agent("nonexistent", graceful=True))

    def test_get_agent_status_unknown_for_missing(self, manager):
        """Verify get_agent_status() returns UNKNOWN for missing agent."""
        from swarm.tmux_manager import AgentStatus

        status = manager.get_agent_status("nonexistent")

        assert status == AgentStatus.UNKNOWN


class TestExceptionsImport:
    """Tests for exception imports."""

    def test_import_base_exception(self):
        """Verify TmuxSwarmError can be imported."""
        from swarm.exceptions import TmuxSwarmError

        assert issubclass(TmuxSwarmError, Exception)

    def test_import_all_exceptions(self):
        """Verify all custom exceptions can be imported."""
        from swarm.exceptions import (
            TmuxSwarmError,
            SessionNotFoundError,
            AgentNotFoundError,
            PaneDeadError,
            SessionCreationError
        )

        # All should be subclasses of TmuxSwarmError
        for exc in [SessionNotFoundError, AgentNotFoundError,
                    PaneDeadError, SessionCreationError]:
            assert issubclass(exc, TmuxSwarmError)

    def test_exception_inheritance(self):
        """Verify exception hierarchy is correct."""
        from swarm.exceptions import (
            TmuxSwarmError,
            SessionNotFoundError,
            AgentNotFoundError,
            PaneDeadError,
            SessionCreationError
        )

        # All custom exceptions should inherit from TmuxSwarmError
        assert SessionNotFoundError.__bases__[0] == TmuxSwarmError
        assert AgentNotFoundError.__bases__[0] == TmuxSwarmError
        assert PaneDeadError.__bases__[0] == TmuxSwarmError
        assert SessionCreationError.__bases__[0] == TmuxSwarmError


class TestPackageExports:
    """Tests for package-level exports."""

    def test_import_tmux_manager(self):
        """Verify TmuxSwarmManager can be imported from swarm package."""
        with patch.dict('sys.modules', {'libtmux': MagicMock()}):
            from swarm import TmuxSwarmManager
            assert TmuxSwarmManager is not None

    def test_import_agent_status(self):
        """Verify AgentStatus can be imported from swarm package."""
        with patch.dict('sys.modules', {'libtmux': MagicMock()}):
            from swarm import AgentStatus
            assert AgentStatus is not None

    def test_import_agent_pane(self):
        """Verify AgentPane can be imported from swarm package."""
        with patch.dict('sys.modules', {'libtmux': MagicMock()}):
            from swarm import AgentPane
            assert AgentPane is not None

    def test_import_tmux_error(self):
        """Verify TmuxSwarmError can be imported from swarm package."""
        from swarm import TmuxSwarmError
        assert TmuxSwarmError is not None

    def test_all_exports_in_dunder_all(self):
        """Verify all expected exports are in __all__."""
        import swarm

        expected = ['TaskQueue', 'SmartWorker',
                    'TmuxSwarmManager', 'AgentStatus', 'AgentPane', 'TmuxSwarmError']

        for name in expected:
            assert name in swarm.__all__, f"{name} not in __all__"


class TestTmuxAvailabilityCheck:
    """Tests for tmux availability checking."""

    def test_start_requires_tmux(self, isolated_swarm_dir, monkeypatch):
        """Verify start() fails if tmux is not installed."""
        import asyncio
        import subprocess
        from swarm.tmux_manager import TmuxSwarmManager
        from swarm.exceptions import SessionCreationError

        mgr = TmuxSwarmManager(cluster_id="test")

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError("tmux not found")

            with pytest.raises(SessionCreationError) as exc_info:
                asyncio.run(mgr.start())

            assert "tmux is not installed" in str(exc_info.value)


class TestSessionInfo:
    """Tests for session info structure."""

    def test_get_session_info_active(self, isolated_swarm_dir):
        """Verify get_session_info() for active session."""
        from swarm.tmux_manager import TmuxSwarmManager, AgentStatus

        mgr = TmuxSwarmManager(cluster_id="test")

        mock_session = MagicMock()
        mock_session.get.side_effect = lambda key: {
            'session_id': '$1',
            'session_name': 'swarm-test'
        }.get(key)
        mock_session.windows = [MagicMock(), MagicMock()]

        mgr._session = mock_session
        mgr._agents["agent-1"] = MagicMock(status=AgentStatus.RUNNING)

        info = mgr.get_session_info()

        assert info['active'] is True
        assert info['session_id'] == '$1'
        assert info['session_name'] == 'swarm-test'
        assert info['windows'] == 2
        assert info['agent_count'] == 1
