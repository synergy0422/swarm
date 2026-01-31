#!/usr/bin/env python3
"""
Semi-black-box E2E test for AutoRescuer with mock tmux manager

Phase 6: Integration Testing - Auto Rescuer E2E Test

Tests AutoRescuer pattern detection and send_enter without real tmux.
Uses mock TmuxSwarmManager for controlled testing.

Key characteristics:
- Semi-black-box: real AutoRescuer logic + mock tmux manager
- Tests end-to-end flow: pattern detection -> send_enter call
- Fast and deterministic (no timing issues)
- No real tmux panes or Master integration required
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from swarm.auto_rescuer import (
    AutoRescuer,
    WaitPatternDetector,
    WaitPattern,
    PatternCategory,
    DETECTION_LINE_COUNT,
    DETECTION_TIME_WINDOW
)

# Mark all tests as unit tests (mock-based, no real tmux integration)
pytestmark = pytest.mark.unit


# ==================== Mock Fixtures ====================

@pytest.fixture
def mock_tmux_manager():
    """
    Create a mock TmuxSwarmManager for testing AutoRescuer.

    This fixture provides a fully configured mock manager with:
    - _agents dict containing mock agents
    - Each agent has pane.send_keys method
    """
    manager = Mock()
    agent = Mock()
    agent.pane = Mock()
    agent.pane.send_keys = Mock()
    manager._agents = {'worker-0': agent}
    return manager


@pytest.fixture
def mock_tmux_manager_multiple_agents():
    """
    Create a mock TmuxSwarmManager with multiple agents.
    Useful for testing multi-worker scenarios.
    """
    manager = MagicMock()
    agents_dict = {}
    for i in range(3):
        agent = Mock()
        agent.pane = Mock()
        agent.pane.send_keys = Mock()
        agents_dict[f'worker-{i}'] = agent
    manager._agents = agents_dict
    return manager


# ==================== Test Helper Functions ====================

def capture_pane_output_mock(manager, worker_id='worker-0'):
    """
    Mock capture pane function - returns output stored on agent.

    In real implementation, this would call:
        manager.capture_pane_output(worker_id)

    For testing, we store output on the agent object
    and retrieve it here.
    """
    agent = manager._agents.get(worker_id)
    if agent:
        return getattr(agent, '_captured_output', '')
    return ''


def set_pane_output_mock(manager, worker_id, output):
    """
    Set mock pane output for testing.

    This simulates what the real capture_pane_output would return
    by storing the output directly on the mock agent.
    """
    agent = manager._agents.get(worker_id)
    if agent:
        agent._captured_output = output


# ==================== Semi-Black-Box AutoRescuer Tests ====================

class TestAutoRescuerSemiBlackBox:
    """
    Semi-black-box tests for AutoRescuer.

    These tests verify the complete flow:
    1. Pattern detection (from pane output)
    2. Auto-rescue decision (enable/disable state)
    3. Action execution (send_enter call)

    We mock the tmux layer but test the real AutoRescuer logic.
    """

    def test_press_enter_auto_rescue_mock(self, mock_tmux_manager):
        """
        Semi-black-box test: Verify AutoRescuer sends Enter for Press ENTER patterns.

        This test:
        1. Creates AutoRescuer with mock tmux manager
        2. Enables auto-rescue
        3. Injects "Press ENTER to continue" pattern via mock output
        4. Verifies send_enter was called on the mock agent

        Note: This is a semi-black-box test - we mock tmux manager but test
        the real AutoRescuer logic. It does NOT require real tmux panes
        or Master integration (which is not yet implemented).
        """
        # Create rescuer with mock manager
        rescuer = AutoRescuer(mock_tmux_manager)
        rescuer.enable()

        # Set mock pane output with Press ENTER pattern
        set_pane_output_mock(mock_tmux_manager, 'worker-0',
                             'Processing...\nPress ENTER to continue...\nDone.')

        # Capture pane output for pattern detection
        output = capture_pane_output_mock(mock_tmux_manager, 'worker-0')
        recent_threshold = datetime.now() - timedelta(seconds=30)

        # Check and rescue - should detect Press ENTER and send Enter
        pattern = rescuer.check_and_rescue('worker-0', output, recent_threshold)

        # Verify pattern was detected
        assert pattern is not None, "Press ENTER pattern should be detected"
        assert pattern.category == PatternCategory.PRESS_ENTER
        assert pattern.should_auto_confirm is True, "Press ENTER should auto-confirm"

        # Verify send_enter was called on the mock agent
        mock_tmux_manager._agents['worker-0'].pane.send_keys.assert_called_once_with('', enter=True)

        # Cleanup
        rescuer.disable()

    def test_auto_rescue_disabled_does_not_send_enter(self, mock_tmux_manager):
        """
        Test: Disabled AutoRescuer does NOT send Enter even for Press ENTER patterns.

        Verifies the conservative default policy (auto-confirm disabled by default).
        """
        # Create rescuer - starts disabled by default
        rescuer = AutoRescuer(mock_tmux_manager)
        assert not rescuer.is_enabled(), "AutoRescuer should be disabled by default"

        # Set mock pane output with Press ENTER pattern
        set_pane_output_mock(mock_tmux_manager, 'worker-0',
                             'Installation complete.\nPress ENTER to continue.')

        # Check and rescue
        output = capture_pane_output_mock(mock_tmux_manager, 'worker-0')
        pattern = rescuer.check_and_rescue('worker-0', output)

        # Pattern detected but NO Enter sent (disabled)
        assert pattern is not None
        assert pattern.category == PatternCategory.PRESS_ENTER
        mock_tmux_manager._agents['worker-0'].pane.send_keys.assert_not_called()

    def test_multiple_workers_auto_rescue(self, mock_tmux_manager_multiple_agents):
        """
        Test: AutoRescuer can handle multiple workers independently.

        Verifies that:
        1. Each worker is tracked separately
        2. send_enter is called only for the worker with the pattern
        """
        rescuer = AutoRescuer(mock_tmux_manager_multiple_agents)
        rescuer.enable()

        # Set pattern on worker-0 only
        set_pane_output_mock(mock_tmux_manager_multiple_agents, 'worker-0',
                             'Task running.\nPress ENTER to continue.')
        # No pattern on worker-1
        set_pane_output_mock(mock_tmux_manager_multiple_agents, 'worker-1',
                             'Task running normally.')

        # Check worker-0 - should trigger auto-rescue
        output_0 = capture_pane_output_mock(mock_tmux_manager_multiple_agents, 'worker-0')
        pattern_0 = rescuer.check_and_rescue('worker-0', output_0)
        assert pattern_0 is not None

        # Check worker-1 - no pattern, no action
        output_1 = capture_pane_output_mock(mock_tmux_manager_multiple_agents, 'worker-1')
        pattern_1 = rescuer.check_and_rescue('worker-1', output_1)
        assert pattern_1 is None

        # Verify send_enter was called ONLY for worker-0
        mock_tmux_manager_multiple_agents._agents['worker-0'].pane.send_keys.assert_called_once_with('', enter=True)
        mock_tmux_manager_multiple_agents._agents['worker-1'].pane.send_keys.assert_not_called()

        rescuer.disable()

    def test_y_n_pattern_does_not_auto_confirm(self, mock_tmux_manager):
        """
        Test: [y/n] patterns are detected but NEVER auto-confirmed.

        Verifies the conservative policy: y/n prompts always require manual intervention.
        """
        rescuer = AutoRescuer(mock_tmux_manager)
        rescuer.enable()

        # Set mock pane output with y/n pattern
        set_pane_output_mock(mock_tmux_manager, 'worker-0',
                             'Continue installation? [y/n]')

        output = capture_pane_output_mock(mock_tmux_manager, 'worker-0')
        pattern = rescuer.check_and_rescue('worker-0', output)

        # Pattern detected
        assert pattern is not None
        assert pattern.category == PatternCategory.INTERACTIVE_CONFIRM
        assert pattern.should_auto_confirm is False

        # Enter NOT sent (even when enabled)
        mock_tmux_manager._agents['worker-0'].pane.send_keys.assert_not_called()

    def test_send_enter_failure_handled_gracefully(self, mock_tmux_manager):
        """
        Test: send_enter failure is handled gracefully.

        Verifies that if pane.send_keys raises an exception,
        the AutoRescuer returns False and doesn't crash.
        """
        rescuer = AutoRescuer(mock_tmux_manager)
        rescuer.enable()

        # Make send_keys raise exception
        mock_tmux_manager._agents['worker-0'].pane.send_keys.side_effect = Exception("Pane is dead")

        set_pane_output_mock(mock_tmux_manager, 'worker-0', 'Press ENTER to continue')
        output = capture_pane_output_mock(mock_tmux_manager, 'worker-0')

        # Should not raise exception, should return False from send_enter
        result = rescuer.send_enter('worker-0')
        assert result is False, "send_enter should return False on failure"

    def test_unknown_worker_returns_none(self, mock_tmux_manager):
        """
        Test: send_enter returns False for unknown worker IDs.
        """
        rescuer = AutoRescuer(mock_tmux_manager)
        result = rescuer.send_enter('nonexistent-worker')
        assert result is False

    def test_chinese_pattern_auto_rescue(self, mock_tmux_manager):
        """
        Test: Chinese "按回车" (press enter) patterns are auto-rescued.
        """
        rescuer = AutoRescuer(mock_tmux_manager)
        rescuer.enable()

        set_pane_output_mock(mock_tmux_manager, 'worker-0',
                             '任务完成。\n按回车继续操作。')

        output = capture_pane_output_mock(mock_tmux_manager, 'worker-0')
        pattern = rescuer.check_and_rescue('worker-0', output)

        assert pattern is not None
        assert pattern.category == PatternCategory.PRESS_ENTER
        assert pattern.should_auto_confirm is True
        mock_tmux_manager._agents['worker-0'].pane.send_keys.assert_called_once_with('', enter=True)

    def test_blacklisted_pattern_blocks_auto_rescue(self, mock_tmux_manager):
        """
        Test: Blacklist keywords block auto-rescue even for Press ENTER patterns.

        Patterns like "Press ENTER to delete" should NOT auto-confirm
        due to the 'delete' blacklist keyword.
        """
        rescuer = AutoRescuer(mock_tmux_manager)
        rescuer.enable()

        # Pattern with blacklist keyword - "delete" is a standalone word
        set_pane_output_mock(mock_tmux_manager, 'worker-0',
                             'Confirmation required.\nPress ENTER to delete the file.')

        output = capture_pane_output_mock(mock_tmux_manager, 'worker-0')
        pattern = rescuer.check_and_rescue('worker-0', output)

        # Pattern detected but auto-confirm blocked by blacklist
        assert pattern is not None
        assert pattern.category == PatternCategory.PRESS_ENTER
        assert pattern.should_auto_confirm is False  # Blocked by blacklist

        # Enter NOT sent due to blacklist
        mock_tmux_manager._agents['worker-0'].pane.send_keys.assert_not_called()


# ==================== Pattern Detection Edge Cases ====================

class TestAutoRescuerEdgeCases:
    """Edge case tests for AutoRescuer with mock tmux manager."""

    def test_empty_output_returns_none(self, mock_tmux_manager):
        """
        Test: Empty pane output returns None (no pattern detected).
        """
        rescuer = AutoRescuer(mock_tmux_manager)
        rescuer.enable()

        set_pane_output_mock(mock_tmux_manager, 'worker-0', '')

        output = capture_pane_output_mock(mock_tmux_manager, 'worker-0')
        pattern = rescuer.check_and_rescue('worker-0', output)

        assert pattern is None
        mock_tmux_manager._agents['worker-0'].pane.send_keys.assert_not_called()

    def test_no_pattern_in_output(self, mock_tmux_manager):
        """
        Test: Normal output without wait patterns returns None.
        """
        rescuer = AutoRescuer(mock_tmux_manager)
        rescuer.enable()

        set_pane_output_mock(mock_tmux_manager, 'worker-0',
                             'Step 1: Processing\nStep 2: Complete\nAll done!')

        output = capture_pane_output_mock(mock_tmux_manager, 'worker-0')
        pattern = rescuer.check_and_rescue('worker-0', output)

        assert pattern is None
        mock_tmux_manager._agents['worker-0'].pane.send_keys.assert_not_called()

    def test_time_threshold_parameter_accepted(self, mock_tmux_manager):
        """
        Test: Time threshold parameter is accepted without error.

        Note: The current implementation accepts recent_threshold but does not
        filter patterns based on when they appeared in the output. The threshold
        is stored on the detected WaitPattern for future use (e.g., by Master
        for deciding when to broadcast HELP state).
        """
        rescuer = AutoRescuer(mock_tmux_manager)
        rescuer.enable()

        set_pane_output_mock(mock_tmux_manager, 'worker-0', 'Press ENTER to continue')

        output = capture_pane_output_mock(mock_tmux_manager, 'worker-0')
        # Pass threshold - should not cause error even if not used for filtering
        old_threshold = datetime.now() - timedelta(seconds=60)
        pattern = rescuer.check_and_rescue('worker-0', output, old_threshold)

        # Pattern detected (time threshold not used for content filtering)
        assert pattern is not None
        assert pattern.category == PatternCategory.PRESS_ENTER

        # Enter sent since enabled and pattern detected
        mock_tmux_manager._agents['worker-0'].pane.send_keys.assert_called_once_with('', enter=True)

    def test_enable_disable_toggle(self, mock_tmux_manager):
        """
        Test: enable() and disable() toggle auto-rescue behavior.
        """
        rescuer = AutoRescuer(mock_tmux_manager)

        # Should start disabled
        assert not rescuer.is_enabled()

        # Enable and verify
        rescuer.enable()
        assert rescuer.is_enabled()

        # Disable and verify
        rescuer.disable()
        assert not rescuer.is_enabled()


# ==================== Run Tests ====================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
