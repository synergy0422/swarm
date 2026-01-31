#!/usr/bin/env python3
"""
Test suite for auto_rescuer.py pattern detection

Phase 6: Integration Testing - Auto Rescuer Pattern Tests

Tests for WaitPatternDetector and AutoRescuer with pytest.
Uses mock tmux_manager for fast, CI-friendly execution.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

from swarm.auto_rescuer import (
    AutoRescuer,
    WaitPatternDetector,
    WaitPattern,
    PatternCategory,
    DETECTION_LINE_COUNT,
    BLACKLIST_KEYWORDS
)

# Mark all tests as unit tests (no real tmux required)
pytestmark = pytest.mark.unit


# ==================== Fixtures ====================

@pytest.fixture
def detector():
    """Fresh WaitPatternDetector for each test."""
    return WaitPatternDetector()


@pytest.fixture
def mock_tmux_manager():
    """Mock TmuxSwarmManager for AutoRescuer tests."""
    mock = Mock()
    mock_agent = Mock()
    mock_agent.pane.send_keys = Mock()
    mock._agents = {'test-worker': mock_agent}
    return mock


@pytest.fixture
def rescuer(mock_tmux_manager):
    """AutoRescuer with mock tmux manager."""
    return AutoRescuer(mock_tmux_manager)


# ==================== Test Classes ====================

class TestWaitPatternDetectorInteractiveConfirm:
    """Test suite for INTERACTIVE_CONFIRM pattern detection."""

    def test_detects_y_n_brackets(self, detector):
        """Test: detects [y/n] and [Y/n] patterns"""
        patterns = [
            "[y/n]",
            "[Y/n]",
            "[y/N]",
            "[Y/N]"
        ]
        for pattern in patterns:
            result = detector.detect(pattern, datetime.now())
            assert result is not None
            assert result.category == PatternCategory.INTERACTIVE_CONFIRM
            assert result.should_auto_confirm is False

    def test_detects_parenthesized_y_n(self, detector):
        """Test: detects (y/n) patterns"""
        patterns = [
            "(y/n)",
            "(Y/n)",
            "Please confirm (y/n)"
        ]
        for pattern in patterns:
            result = detector.detect(pattern, datetime.now())
            assert result is not None
            assert result.category == PatternCategory.INTERACTIVE_CONFIRM

    def test_detects_y_or_n_text(self, detector):
        """Test: detects 'y or n' and 'yes or no' text patterns"""
        patterns = [
            "y or n",
            "Y or n",
            "yes or no"
        ]
        for pattern in patterns:
            result = detector.detect(pattern, datetime.now())
            assert result is not None
            assert result.category == PatternCategory.INTERACTIVE_CONFIRM

    def test_never_auto_confirms_interactive(self, detector):
        """Test: INTERACTIVE_CONFIRM always has should_auto_confirm=False"""
        for pattern in ["[y/n]", "(y/n)", "y or n"]:
            result = detector.detect(pattern, datetime.now())
            assert result.should_auto_confirm is False

    def test_case_insensitive_interactive(self, detector):
        """Test: Interactive patterns are case-insensitive"""
        patterns = ["[Y/N]", "[Y/n]", "[y/N]"]
        for pattern in patterns:
            result = detector.detect(pattern, datetime.now())
            assert result is not None
            assert result.category == PatternCategory.INTERACTIVE_CONFIRM


class TestWaitPatternDetectorPressEnter:
    """Test suite for PRESS_ENTER pattern detection."""

    def test_detects_press_enter(self, detector):
        """Test: detects 'Press ENTER' patterns"""
        patterns = [
            "Press ENTER to continue",
            "Press Enter to proceed",
            "Press RETURN to continue"
        ]
        for pattern in patterns:
            result = detector.detect(pattern, datetime.now())
            assert result is not None
            assert result.category == PatternCategory.PRESS_ENTER
            assert result.should_auto_confirm is True

    def test_detects_hit_enter(self, detector):
        """Test: detects 'hit enter' patterns"""
        patterns = [
            "hit enter to continue",
            "Hit Enter to proceed"
        ]
        for pattern in patterns:
            result = detector.detect(pattern, datetime.now())
            assert result is not None
            assert result.category == PatternCategory.PRESS_ENTER

    def test_detects_press_any_key(self, detector):
        """Test: detects 'press any key' patterns"""
        pattern = "Press any key to continue"
        result = detector.detect(pattern, datetime.now())
        assert result is not None
        assert result.category == PatternCategory.PRESS_ENTER

    def test_press_enter_auto_confirm_safe(self, detector):
        """Test: PRESS_ENTER has should_auto_confirm=True (safe patterns)"""
        result = detector.detect("Press ENTER to continue", datetime.now())
        assert result.should_auto_confirm is True

    def test_case_insensitive_press_enter(self, detector):
        """Test: Press ENTER patterns are case-insensitive"""
        patterns = ["PRESS ENTER TO CONTINUE", "press Enter to Continue"]
        for pattern in patterns:
            result = detector.detect(pattern, datetime.now())
            assert result is not None
            assert result.category == PatternCategory.PRESS_ENTER


class TestWaitPatternDetectorChinese:
    """Test suite for Chinese pattern detection."""

    def test_detects_chinese_press_enter(self, detector):
        """Test: detects Chinese 'press enter' patterns"""
        patterns = [
            "按回车继续",      # Press enter to continue
            "回车继续",        # Press enter continue
            "请按回车键",      # Please press enter key
        ]
        for pattern in patterns:
            result = detector.detect(pattern, datetime.now())
            assert result is not None
            assert result.category == PatternCategory.PRESS_ENTER
            assert result.should_auto_confirm is True

    def test_detects_chinese_confirm(self, detector):
        """Test: detects Chinese confirm patterns"""
        patterns = [
            "请确认操作",      # Please confirm operation
            "确定吗？",        # Are you sure?
        ]
        for pattern in patterns:
            result = detector.detect(pattern, datetime.now())
            assert result is not None
            assert result.category == PatternCategory.CONFIRM_PROMPT

    def test_chinese_patterns_auto_confirm_safe(self, detector):
        """Test: Chinese patterns without delete keywords auto-confirm"""
        pattern = "按回车继续"
        result = detector.detect(pattern, datetime.now())
        assert result.should_auto_confirm is True


class TestBlacklistBlocking:
    """Test suite for blacklist keyword blocking."""

    def test_blacklist_blocks_delete_patterns(self, detector):
        """Test: 'delete' keyword blocks auto-confirm"""
        patterns = [
            "Press ENTER to delete all files",
            "Press ENTER to delete",
            "Press Enter to remove file"
        ]
        for pattern in patterns:
            result = detector.detect(pattern, datetime.now())
            assert result is not None
            assert result.should_auto_confirm is False

    def test_blacklist_blocks_rm_rf(self, detector):
        """Test: 'rm -rf' blocks auto-confirm"""
        pattern = "Press enter to rm -rf /tmp/data"
        result = detector.detect(pattern, datetime.now())
        assert result.should_auto_confirm is False

    def test_blacklist_blocks_sudo(self, detector):
        """Test: 'sudo' blocks auto-confirm"""
        pattern = "Press enter with sudo access"
        result = detector.detect(pattern, datetime.now())
        assert result.should_auto_confirm is False

    def test_blacklist_blocks_password(self, detector):
        """Test: 'password' blocks auto-confirm"""
        # Use a press enter pattern with password keyword
        pattern = "Press ENTER to enter password"
        result = detector.detect(pattern, datetime.now())
        assert result is not None
        assert result.should_auto_confirm is False

    def test_blacklist_blocks_prod(self, detector):
        """Test: 'prod' or '生产' blocks auto-confirm"""
        patterns = [
            "Press enter for production deployment",
            "按回车确认生产环境"
        ]
        for pattern in patterns:
            result = detector.detect(pattern, datetime.now())
            assert result.should_auto_confirm is False

    def test_blacklist_blocks_token(self, detector):
        """Test: 'token' blocks auto-confirm"""
        pattern = "Press enter to generate token"
        result = detector.detect(pattern, datetime.now())
        assert result.should_auto_confirm is False

    def test_blacklist_blocks_ssh(self, detector):
        """Test: 'ssh' blocks auto-confirm"""
        pattern = "Press enter to connect via ssh"
        result = detector.detect(pattern, datetime.now())
        assert result.should_auto_confirm is False

    def test_blacklist_still_returns_pattern(self, detector):
        """Test: Blacklist blocks auto-confirm but pattern is still detected"""
        pattern = "Press ENTER to delete all"
        result = detector.detect(pattern, datetime.now())
        assert result is not None
        assert result.category == PatternCategory.PRESS_ENTER
        assert result.should_auto_confirm is False

    def test_blacklist_keywords_list_complete(self, detector):
        """Test: BLACKLIST_KEYWORDS contains expected keywords"""
        expected_keywords = [
            'delete', 'rm -rf', 'sudo', 'password', 'token', 'ssh',
            '生产', 'prod'
        ]
        for keyword in expected_keywords:
            assert keyword in BLACKLIST_KEYWORDS


class TestPatternPriority:
    """Test suite for pattern detection priority order."""

    def test_interactive_has_priority_over_press_enter(self, detector):
        """Test: [y/n] has priority over Press ENTER in same text"""
        text = "Continue? [y/n] or press ENTER to skip"
        result = detector.detect(text, datetime.now())
        assert result.category == PatternCategory.INTERACTIVE_CONFIRM

    def test_press_enter_has_priority_over_confirm(self, detector):
        """Test: Press ENTER has priority over confirm in same text"""
        text = "Press ENTER to confirm"
        result = detector.detect(text, datetime.now())
        assert result.category == PatternCategory.PRESS_ENTER

    def test_first_match_wins_in_same_category(self, detector):
        """Test: First matching pattern in category is returned"""
        text = "Option 1: [y/n]\nOption 2: [Y/n]"
        result = detector.detect(text, datetime.now())
        assert result.matched_text == "[y/n]"

    def test_priority_order_is_correct(self, detector):
        """Test: Priority: INTERACTIVE_CONFIRM > PRESS_ENTER > CONFIRM_PROMPT"""
        # All three in one text - should get INTERACTIVE_CONFIRM (highest)
        text = "[y/n] or Press ENTER to continue or confirm"
        result = detector.detect(text, datetime.now())
        assert result.category == PatternCategory.INTERACTIVE_CONFIRM

    def test_confirm_prompt_detected_when_alone(self, detector):
        """Test: CONFIRM_PROMPT detected when no higher priority patterns"""
        text = "Please confirm your choice"
        result = detector.detect(text, datetime.now())
        assert result.category == PatternCategory.CONFIRM_PROMPT


class TestLineCountLimit:
    """Test suite for line count limit (DETECTION_LINE_COUNT)."""

    def test_only_checks_last_20_lines(self, detector):
        """Test: Only last 20 lines are checked for patterns"""
        # Create 25 lines of output with pattern in line 0
        lines = ["Normal line"] * 25
        lines[0] = "Press ENTER to continue"  # Should be ignored
        output = "\n".join(lines)

        result = detector.detect(output, datetime.now())
        assert result is None  # Pattern not in last 20 lines

    def test_detects_pattern_in_last_20_lines(self, detector):
        """Test: Pattern in last 20 lines is detected"""
        lines = ["Normal line"] * 25
        lines[22] = "Press ENTER to continue"  # Should be detected (indices 5-24 are last 20)
        output = "\n".join(lines)

        result = detector.detect(output, datetime.now())
        assert result is not None
        assert result.category == PatternCategory.PRESS_ENTER

    def test_empty_output_returns_none(self, detector):
        """Test: Empty or None output returns None"""
        assert detector.detect("", datetime.now()) is None
        assert detector.detect(None, datetime.now()) is None

    def test_pattern_at_exactly_line_20(self, detector):
        """Test: Pattern at line 20 (index 19) is detected"""
        lines = ["Normal line"] * 20
        lines[19] = "Press ENTER"  # Exactly at line 20 (last of 20)
        output = "\n".join(lines)

        result = detector.detect(output, datetime.now())
        assert result is not None

    def test_pattern_at_line_21_not_detected(self, detector):
        """Test: Pattern at line 21 (index 20) is NOT detected"""
        # With 22 lines (indices 0-21), last 20 are indices 2-21
        # So pattern at index 1 (line 2) is NOT in the last 20
        lines = ["Normal line"] * 22
        lines[1] = "Press ENTER"  # Outside last 20 (indices 2-21 are last 20)
        output = "\n".join(lines)

        result = detector.detect(output, datetime.now())
        assert result is None


class TestAutoRescuerIntegration:
    """Test suite for AutoRescuer with mocked tmux_manager."""

    def test_send_enter_calls_pane_send_keys(self, rescuer, mock_tmux_manager):
        """Test: send_enter calls pane.send_keys with empty string and enter=True"""
        result = rescuer.send_enter('test-worker')
        assert result is True
        mock_tmux_manager._agents['test-worker'].pane.send_keys.assert_called_once_with('', enter=True)

    def test_send_enter_returns_false_for_unknown_agent(self, rescuer):
        """Test: send_enter returns False for unknown agent"""
        result = rescuer.send_enter('unknown-agent')
        assert result is False

    def test_send_enter_handles_exception(self, rescuer, mock_tmux_manager):
        """Test: send_enter returns False on exception"""
        mock_tmux_manager._agents['test-worker'].pane.send_keys.side_effect = Exception("Pane dead")
        result = rescuer.send_enter('test-worker')
        assert result is False

    def test_enabled_rescuer_sends_enter_for_press_enter(self, rescuer, mock_tmux_manager):
        """Test: Enabled rescuer sends Enter for PRESS_ENTER pattern"""
        rescuer.enable()
        output = "Press ENTER to continue"

        pattern = rescuer.check_and_rescue('test-worker', output, datetime.now())

        assert pattern is not None
        mock_tmux_manager._agents['test-worker'].pane.send_keys.assert_called_once_with('', enter=True)

    def test_disabled_rescuer_does_not_send_enter(self, rescuer, mock_tmux_manager):
        """Test: Disabled rescuer does NOT send Enter (default behavior)"""
        # Disabled by default
        output = "Press ENTER to continue"

        pattern = rescuer.check_and_rescue('test-worker', output, datetime.now())

        assert pattern is not None
        mock_tmux_manager._agents['test-worker'].pane.send_keys.assert_not_called()

    def test_auto_confirm_disabled_by_default(self, rescuer):
        """Test: auto-confirm is disabled by default"""
        assert rescuer.is_enabled() is False

    def test_enable_and_disable(self, rescuer):
        """Test: enable() and disable() toggle auto-confirm"""
        assert rescuer.is_enabled() is False
        rescuer.enable()
        assert rescuer.is_enabled() is True
        rescuer.disable()
        assert rescuer.is_enabled() is False

    def test_never_auto_confirms_interactive_patterns(self, rescuer, mock_tmux_manager):
        """Test: NEVER auto-confirms y/n patterns even when enabled"""
        rescuer.enable()
        output = "Continue? [y/n]"

        pattern = rescuer.check_and_rescue('test-worker', output, datetime.now())

        # Pattern detected but no Enter sent
        assert pattern is not None
        assert pattern.category == PatternCategory.INTERACTIVE_CONFIRM
        mock_tmux_manager._agents['test-worker'].pane.send_keys.assert_not_called()

    def test_no_pattern_returns_none(self, rescuer):
        """Test: check_and_rescue returns None for safe output"""
        output = "Normal processing\nNo prompts here"
        pattern = rescuer.check_and_rescue('test-worker', output, datetime.now())
        assert pattern is None

    def test_should_request_help_for_interactive(self, rescuer):
        """Test: should_request_help returns True for INTERACTIVE_CONFIRM"""
        pattern = WaitPattern(
            category=PatternCategory.INTERACTIVE_CONFIRM,
            matched_text="[y/n]",
            line_number=0,
            should_auto_confirm=False,
            timestamp=datetime.now()
        )
        assert rescuer.should_request_help(pattern) is True

    def test_should_not_request_help_for_safe_press_enter(self, rescuer):
        """Test: should_request_help returns False for safe PRESS_ENTER"""
        pattern = WaitPattern(
            category=PatternCategory.PRESS_ENTER,
            matched_text="Press ENTER",
            line_number=0,
            should_auto_confirm=True,  # Safe (not blacklisted)
            timestamp=datetime.now()
        )
        assert rescuer.should_request_help(pattern) is False

    def test_should_request_help_for_blacklisted_press_enter(self, rescuer):
        """Test: should_request_help returns True for blacklisted PRESS_ENTER"""
        pattern = WaitPattern(
            category=PatternCategory.PRESS_ENTER,
            matched_text="Press ENTER",
            line_number=0,
            should_auto_confirm=False,  # Blacklisted
            timestamp=datetime.now()
        )
        assert rescuer.should_request_help(pattern) is True


class TestWaitPatternDataclass:
    """Test suite for WaitPattern dataclass attributes."""

    def test_wait_pattern_has_all_attributes(self, detector):
        """Test: WaitPattern contains all required attributes"""
        pattern = detector.detect("Press ENTER to continue", datetime.now())
        assert pattern is not None
        assert hasattr(pattern, 'category')
        assert hasattr(pattern, 'matched_text')
        assert hasattr(pattern, 'line_number')
        assert hasattr(pattern, 'should_auto_confirm')
        assert hasattr(pattern, 'timestamp')

    def test_wait_pattern_category_values(self, detector):
        """Test: PatternCategory enum has expected values"""
        assert PatternCategory.INTERACTIVE_CONFIRM.value == 'interactive_confirm'
        assert PatternCategory.PRESS_ENTER.value == 'press_enter'
        assert PatternCategory.CONFIRM_PROMPT.value == 'confirm_prompt'
        assert PatternCategory.NONE.value == 'none'


# ==================== Run Tests ====================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
