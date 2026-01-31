#!/usr/bin/env python3
"""
Test suite for auto_rescuer.py
Phase 4: Master Implementation - Auto Rescuer Tests

Tests for WaitPatternDetector and AutoRescuer classes.
Uses mock for tmux_manager to avoid actual tmux dependency.
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

from swarm.auto_rescuer import (
    AutoRescuer,
    WaitPatternDetector,
    WaitPattern,
    PatternCategory,
    DETECTION_LINE_COUNT,
    DETECTION_TIME_WINDOW,
    BLACKLIST_KEYWORDS
)


class TestWaitPatternDetector(unittest.TestCase):
    """Test suite for WaitPatternDetector"""

    def setUp(self):
        """Set up test fixtures."""
        self.detector = WaitPatternDetector()
        self.recent_threshold = datetime.now() - timedelta(seconds=DETECTION_TIME_WINDOW)

    def test_detect_y_n_patterns(self):
        """Test: detects [y/n], [Y/n], (y/n) patterns"""
        test_cases = [
            "Do you want to continue? [y/n]",
            "Confirm this action [Y/n]",
            "Please confirm (y/n):",
            "Enter y or n to continue",
            "Select yes or no",
        ]

        for output in test_cases:
            with self.subTest(output=output):
                pattern = self.detector.detect(output, self.recent_threshold)
                self.assertIsNotNone(pattern)
                self.assertEqual(pattern.category, PatternCategory.INTERACTIVE_CONFIRM)
                self.assertFalse(pattern.should_auto_confirm)

    def test_detect_press_enter(self):
        """Test: detects Press ENTER to continue patterns"""
        test_cases = [
            ("Press ENTER to continue...", True),
            ("Press Return to proceed", True),
            ("hit enter to continue", True),
            # "Press any key to continue" contains "key" which is blacklisted
            ("Press any key to continue", False),
        ]

        for output, expected_auto_confirm in test_cases:
            with self.subTest(output=output):
                pattern = self.detector.detect(output, self.recent_threshold)
                self.assertIsNotNone(pattern)
                self.assertEqual(pattern.category, PatternCategory.PRESS_ENTER)
                self.assertEqual(pattern.should_auto_confirm, expected_auto_confirm)

    def test_detect_chinese_press_enter(self):
        """Test: detects Chinese press enter patterns"""
        test_cases = [
            "按回车继续",
            "回车继续",
            "请按回车键",
        ]

        for output in test_cases:
            with self.subTest(output=output):
                pattern = self.detector.detect(output, self.recent_threshold)
                self.assertIsNotNone(pattern)
                self.assertEqual(pattern.category, PatternCategory.PRESS_ENTER)
                self.assertTrue(pattern.should_auto_confirm)

    def test_detect_confirm_prompt(self):
        """Test: detects confirm, are you sure patterns"""
        test_cases = [
            "Please confirm your choice",
            "Are you sure you want to proceed?",
            "请确认操作",
            "确定吗？",
        ]

        for output in test_cases:
            with self.subTest(output=output):
                pattern = self.detector.detect(output, self.recent_threshold)
                self.assertIsNotNone(pattern)
                self.assertEqual(pattern.category, PatternCategory.CONFIRM_PROMPT)
                self.assertFalse(pattern.should_auto_confirm)

    def test_detect_none_returns_none(self):
        """Test: no pattern returns None"""
        output = "This is normal output\nNo prompts here\nJust processing data"
        pattern = self.detector.detect(output, self.recent_threshold)
        self.assertIsNone(pattern)

    def test_detect_only_last_20_lines(self):
        """Test: ignores patterns in older lines (only checks last 20)"""
        # Create 25 lines of output
        lines = ["Normal line"] * 25
        # Put pattern in line 0 (should be ignored - not in last 20)
        lines[0] = "Press ENTER to continue"

        output = "\n".join(lines)
        pattern = self.detector.detect(output, self.recent_threshold)

        # Pattern should not be detected (it's outside last 20 lines)
        self.assertIsNone(pattern)

    def test_detect_pattern_in_last_20_lines(self):
        """Test: detects patterns in last 20 lines"""
        # Create 25 lines of output
        lines = ["Normal line"] * 25
        # Put pattern in line 22 (should be detected - in last 20)
        lines[22] = "Press ENTER to continue"

        output = "\n".join(lines)
        pattern = self.detector.detect(output, self.recent_threshold)

        # Pattern should be detected
        self.assertIsNotNone(pattern)
        self.assertEqual(pattern.category, PatternCategory.PRESS_ENTER)

    def test_blacklist_blocks_auto_confirm(self):
        """Test: blacklist keywords (delete, rm -rf, sudo) block auto-confirm"""
        test_cases = [
            "Press ENTER to delete all files",
            "hit enter to rm -rf /tmp/data",
            "Press return with sudo access",
            "按回车确认删除",
            "回车继续以删除",
        ]

        for output in test_cases:
            with self.subTest(output=output):
                pattern = self.detector.detect(output, self.recent_threshold)
                self.assertIsNotNone(pattern)
                # Pattern detected but auto-confirm blocked
                self.assertFalse(pattern.should_auto_confirm)

    def test_case_insensitive_detection(self):
        """Test: [Y/N] matches [y/n] (case-insensitive)"""
        test_cases = [
            "Continue? [Y/N]",
            "Continue? [y/n]",
            "Continue? [Y/n]",
            "PRESS ENTER TO CONTINUE",
            "press Enter to Continue",
        ]

        for output in test_cases:
            with self.subTest(output=output):
                pattern = self.detector.detect(output, self.recent_threshold)
                self.assertIsNotNone(pattern)

    def test_priority_order_interactive_first(self):
        """Test: interactive confirm has priority over press enter"""
        output = "Continue? [y/n] or press ENTER to skip"
        pattern = self.detector.detect(output, self.recent_threshold)

        # Should detect interactive confirm (higher priority)
        self.assertEqual(pattern.category, PatternCategory.INTERACTIVE_CONFIRM)

    def test_empty_output_returns_none(self):
        """Test: empty output returns None"""
        pattern = self.detector.detect("", self.recent_threshold)
        self.assertIsNone(pattern)

        pattern = self.detector.detect(None, self.recent_threshold)
        self.assertIsNone(pattern)

    def test_blacklist_keywords_list(self):
        """Test: BLACKLIST_KEYWORDS contains expected keywords"""
        expected_keywords = [
            'delete', 'rm -rf', 'sudo', 'password',
            '生产', 'prod'
        ]

        for keyword in expected_keywords:
            with self.subTest(keyword=keyword):
                self.assertIn(keyword, BLACKLIST_KEYWORDS)


class TestAutoRescuer(unittest.TestCase):
    """Test suite for AutoRescuer"""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock tmux manager
        self.mock_tmux = Mock()
        self.mock_agent = Mock()
        self.mock_agent.pane.send_keys = Mock()
        self.mock_tmux._agents = {'agent-1': self.mock_agent}

        self.rescuer = AutoRescuer(self.mock_tmux)
        self.recent_threshold = datetime.now() - timedelta(seconds=DETECTION_TIME_WINDOW)

    def test_auto_confirm_disabled_by_default(self):
        """Test: auto-confirm is disabled by default"""
        self.assertFalse(self.rescuer.is_enabled())

    def test_enable_auto_confirm(self):
        """Test: enable() enables auto-confirm"""
        self.rescuer.enable()
        self.assertTrue(self.rescuer.is_enabled())

    def test_disable_auto_confirm(self):
        """Test: disable() disables auto-confirm"""
        self.rescuer.enable()
        self.rescuer.disable()
        self.assertFalse(self.rescuer.is_enabled())

    def test_check_and_rescue_detects_pattern(self):
        """Test: check_and_rescue detects and returns pattern"""
        output = "Press ENTER to continue"
        pattern = self.rescuer.check_and_rescue('agent-1', output, self.recent_threshold)

        self.assertIsNotNone(pattern)
        self.assertEqual(pattern.category, PatternCategory.PRESS_ENTER)

    def test_check_and_rescue_no_pattern_returns_none(self):
        """Test: check_and_rescue returns None for safe output"""
        output = "Normal processing\nNo prompts here"
        pattern = self.rescuer.check_and_rescue('agent-1', output, self.recent_threshold)

        self.assertIsNone(pattern)

    def test_check_and_rescue_sends_enter_when_enabled(self):
        """Test: sends Enter key when enabled and PRESS_ENTER pattern"""
        self.rescuer.enable()
        output = "Press ENTER to continue"

        pattern = self.rescuer.check_and_rescue('agent-1', output, self.recent_threshold)

        # Enter key should be sent
        self.mock_agent.pane.send_keys.assert_called_once_with('', enter=True)

    def test_check_and_rescue_no_enter_when_disabled(self):
        """Test: does NOT send Enter when disabled"""
        # Disabled by default
        output = "Press ENTER to continue"

        self.rescuer.check_and_rescue('agent-1', output, self.recent_threshold)

        # Enter key should NOT be sent
        self.mock_agent.pane.send_keys.assert_not_called()

    def test_should_request_help_for_interactive(self):
        """Test: should_request_help returns True for INTERACTIVE_CONFIRM"""
        pattern = WaitPattern(
            category=PatternCategory.INTERACTIVE_CONFIRM,
            matched_text="[y/n]",
            line_number=0,
            should_auto_confirm=False,
            timestamp=datetime.now()
        )

        self.assertTrue(self.rescuer.should_request_help(pattern))

    def test_should_request_help_for_confirm_prompt(self):
        """Test: should_request_help returns True for CONFIRM_PROMPT"""
        pattern = WaitPattern(
            category=PatternCategory.CONFIRM_PROMPT,
            matched_text="confirm",
            line_number=0,
            should_auto_confirm=False,
            timestamp=datetime.now()
        )

        self.assertTrue(self.rescuer.should_request_help(pattern))

    def test_should_not_request_help_for_safe_press_enter(self):
        """Test: should_request_help returns False for safe PRESS_ENTER"""
        pattern = WaitPattern(
            category=PatternCategory.PRESS_ENTER,
            matched_text="Press ENTER",
            line_number=0,
            should_auto_confirm=True,  # Safe (not blacklisted)
            timestamp=datetime.now()
        )

        self.assertFalse(self.rescuer.should_request_help(pattern))

    def test_should_request_help_for_blacklisted_press_enter(self):
        """Test: should_request_help returns True for blacklisted PRESS_ENTER"""
        pattern = WaitPattern(
            category=PatternCategory.PRESS_ENTER,
            matched_text="Press ENTER",
            line_number=0,
            should_auto_confirm=False,  # Blacklisted
            timestamp=datetime.now()
        )

        self.assertTrue(self.rescuer.should_request_help(pattern))

    def test_send_enter_sends_empty_string_with_enter(self):
        """Test: send_enter sends empty string with enter=True"""
        result = self.rescuer.send_enter('agent-1')

        # Should send empty string with enter
        self.mock_agent.pane.send_keys.assert_called_once_with('', enter=True)
        self.assertTrue(result)

    def test_send_enter_returns_false_for_unknown_agent(self):
        """Test: send_enter returns False for unknown agent"""
        result = self.rescuer.send_enter('unknown-agent')
        self.assertFalse(result)

    def test_send_enter_handles_exceptions(self):
        """Test: send_enter returns False on exception"""
        # Make send_keys raise an exception
        self.mock_agent.pane.send_keys.side_effect = Exception("Pane dead")

        result = self.rescuer.send_enter('agent-1')
        self.assertFalse(result)

    def test_never_auto_confirms_interactive_patterns(self):
        """Test: NEVER auto-confirms y/n patterns even when enabled"""
        self.rescuer.enable()
        output = "Continue? [y/n]"

        pattern = self.rescuer.check_and_rescue('agent-1', output, self.recent_threshold)

        # Pattern detected but no Enter sent
        self.assertIsNotNone(pattern)
        self.assertEqual(pattern.category, PatternCategory.INTERACTIVE_CONFIRM)
        self.mock_agent.pane.send_keys.assert_not_called()

    def test_check_and_rescue_uses_default_time_threshold(self):
        """Test: uses 30 second default threshold when not provided"""
        output = "Press ENTER to continue"

        # Not providing recent_threshold
        pattern = self.rescuer.check_and_rescue('agent-1', output)

        self.assertIsNotNone(pattern)
        # Should have used default 30 second threshold


if __name__ == '__main__':
    unittest.main(verbosity=2)
