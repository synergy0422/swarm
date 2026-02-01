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
from unittest.mock import Mock
from datetime import datetime, timedelta

from swarm.auto_rescuer import (
    AutoRescuer,
    PatternCategory
)

# Mark all tests as integration tests (semi-black-box with mock tmux manager)
pytestmark = pytest.mark.integration


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


# ==================== Semi-Black-Box AutoRescuer Test ====================

def test_press_enter_auto_rescue_mock(mock_tmux_manager):
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


# ==================== Run Tests ====================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
