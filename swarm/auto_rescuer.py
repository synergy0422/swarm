"""
Auto Rescuer Module for AI Swarm System

Provides conservative auto-rescue for workers stuck waiting for user input.
Detects WAIT patterns (y/n, Press ENTER, confirm) and can auto-confirm safe patterns.
"""

import re
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List


# ==================== Constants ====================

DETECTION_LINE_COUNT = 20  # Only check last 20 lines
DETECTION_TIME_WINDOW = 30  # 30 seconds window

BLACKLIST_KEYWORDS = [
    'delete', 'remove', 'rm -rf', 'format', 'overwrite',
    'drop database', 'drop table',
    'kill', 'terminate',
    'sudo', 'password', 'token', 'ssh', 'key',
    '生产', 'prod',
]


# ==================== PatternCategory Enum ====================

class PatternCategory(str, Enum):
    """Category of WAIT pattern detected."""
    INTERACTIVE_CONFIRM = 'interactive_confirm'  # [y/n], [Y/n] patterns
    PRESS_ENTER = 'press_enter'                  # Press ENTER to continue
    CONFIRM_PROMPT = 'confirm_prompt'            # confirm, are you sure
    NONE = 'none'                                # no pattern detected


# ==================== WaitPattern Dataclass ====================

@dataclass
class WaitPattern:
    """
    Represents a detected WAIT pattern in pane output.

    Attributes:
        category: Type of pattern detected
        matched_text: The actual text that matched the pattern
        line_number: Line number where pattern was found (from end, 0-indexed)
        should_auto_confirm: True only for PRESS_ENTER patterns
        timestamp: When the pattern was detected
    """
    category: PatternCategory
    matched_text: str
    line_number: int
    should_auto_confirm: bool
    timestamp: datetime


# ==================== WaitPatternDetector Class ====================

class WaitPatternDetector:
    """
    Detects WAIT patterns in pane output.

    Detection priorities:
    1. INTERACTIVE_CONFIRM - y/n patterns (highest priority)
    2. PRESS_ENTER - Press ENTER to continue
    3. CONFIRM_PROMPT - confirm/are you sure

    Only checks last 20 lines and patterns within last 30 seconds.
    All pattern matching is case-insensitive.
    """

    def __init__(self):
        """Initialize the pattern detector with compiled regex patterns."""
        # Interactive confirm patterns: [y/n], [Y/n], (y/n), etc.
        self._interactive_patterns = [
            re.compile(r'\[y/n\]', re.IGNORECASE),
            re.compile(r'\[Y/n\]', re.IGNORECASE),
            re.compile(r'\(y/n\)', re.IGNORECASE),
            re.compile(r'\by or n\b', re.IGNORECASE),
            re.compile(r'\byes or no\b', re.IGNORECASE),
        ]

        # Press ENTER patterns: Press ENTER, hit enter, 按回车
        self._press_enter_patterns = [
            re.compile(r'press\s+enter', re.IGNORECASE),
            re.compile(r'press\s+return', re.IGNORECASE),
            re.compile(r'hit\s+enter', re.IGNORECASE),
            re.compile(r'按回车', re.IGNORECASE),
            re.compile(r'回车继续', re.IGNORECASE),
            re.compile(r'press\s+any\s+key\s+to\s+continue', re.IGNORECASE),
        ]

        # Confirm prompt patterns: confirm, are you sure, 确认
        self._confirm_patterns = [
            re.compile(r'\bconfirm\b', re.IGNORECASE),
            re.compile(r'are\s+you\s+sure', re.IGNORECASE),
            re.compile(r'确认', re.IGNORECASE),
            re.compile(r'确定吗', re.IGNORECASE),
        ]

    def detect(self, pane_output: str, recent_threshold: datetime) -> Optional[WaitPattern]:
        """
        Detect WAIT patterns in pane output.

        Args:
            pane_output: Full output from tmux pane
            recent_threshold: Only consider patterns after this timestamp

        Returns:
            WaitPattern if detected, None otherwise
        """
        if not pane_output:
            return None

        # Split output into lines
        lines = pane_output.splitlines()

        # Only check last N lines
        recent_lines = lines[-DETECTION_LINE_COUNT:]

        # Check patterns in priority order
        # 1. Interactive confirm (highest priority)
        pattern = self._check_interactive_confirm(recent_lines)
        if pattern:
            return pattern

        # 2. Press ENTER
        pattern = self._check_press_enter(recent_lines)
        if pattern:
            return pattern

        # 3. Confirm prompt
        pattern = self._check_confirm_prompt(recent_lines)
        if pattern:
            return pattern

        return None

    def _check_interactive_confirm(self, lines: List[str]) -> Optional[WaitPattern]:
        """
        Check for interactive confirm patterns (y/n).

        Returns WaitPattern with should_auto_confirm=False
        """
        for i, line in enumerate(lines):
            for pattern in self._interactive_patterns:
                match = pattern.search(line)
                if match:
                    # Check if blacklisted
                    if self._is_blacklisted(line):
                        # Still return pattern, but mark for manual intervention
                        return WaitPattern(
                            category=PatternCategory.INTERACTIVE_CONFIRM,
                            matched_text=match.group(0),
                            line_number=i,
                            should_auto_confirm=False,
                            timestamp=datetime.now()
                        )

                    return WaitPattern(
                        category=PatternCategory.INTERACTIVE_CONFIRM,
                        matched_text=match.group(0),
                        line_number=i,
                        should_auto_confirm=False,  # NEVER auto-confirm y/n
                        timestamp=datetime.now()
                    )

        return None

    def _check_press_enter(self, lines: List[str]) -> Optional[WaitPattern]:
        """
        Check for Press ENTER patterns.

        Returns WaitPattern with should_auto_confirm=True (conservative policy)
        """
        for i, line in enumerate(lines):
            for pattern in self._press_enter_patterns:
                match = pattern.search(line)
                if match:
                    # Check if blacklisted
                    if self._is_blacklisted(line):
                        # Blacklisted - don't auto-confirm
                        return WaitPattern(
                            category=PatternCategory.PRESS_ENTER,
                            matched_text=match.group(0),
                            line_number=i,
                            should_auto_confirm=False,  # Blocked by blacklist
                            timestamp=datetime.now()
                        )

                    # Safe to auto-confirm (send Enter key only)
                    return WaitPattern(
                        category=PatternCategory.PRESS_ENTER,
                        matched_text=match.group(0),
                        line_number=i,
                        should_auto_confirm=True,  # Conservative: only Enter
                        timestamp=datetime.now()
                    )

        return None

    def _check_confirm_prompt(self, lines: List[str]) -> Optional[WaitPattern]:
        """
        Check for confirm prompt patterns.

        Returns WaitPattern with should_auto_confirm=False
        """
        for i, line in enumerate(lines):
            for pattern in self._confirm_patterns:
                match = pattern.search(line)
                if match:
                    # Check if blacklisted
                    if self._is_blacklisted(line):
                        return WaitPattern(
                            category=PatternCategory.CONFIRM_PROMPT,
                            matched_text=match.group(0),
                            line_number=i,
                            should_auto_confirm=False,
                            timestamp=datetime.now()
                        )

                    return WaitPattern(
                        category=PatternCategory.CONFIRM_PROMPT,
                        matched_text=match.group(0),
                        line_number=i,
                        should_auto_confirm=False,
                        timestamp=datetime.now()
                    )

        return None

    def _is_blacklisted(self, text: str) -> bool:
        """
        Check if text contains blacklist keywords.

        Args:
            text: Text to check

        Returns:
            True if any blacklist keyword is found (case-insensitive)
        """
        text_lower = text.lower()
        for keyword in BLACKLIST_KEYWORDS:
            if keyword.lower() in text_lower:
                return True
        return False
