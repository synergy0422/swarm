#!/usr/bin/env python3
"""
Auto Rescuer Module for AI Swarm System

Provides automatic rescue for interactive prompts in tmux panes.
Detects WAIT/confirm/press-enter patterns and executes safe auto-confirm.

Features:
- Pattern classification: AUTO_ENTER, MANUAL_CONFIRM, DANGEROUS
- Per-window cooldown mechanism (30 seconds default)
- Dangerous operation blocking (rm -rf, DROP, TRUNCATE, etc.)
- Dry-run mode for testing
"""

import os
import re
import time
from typing import Dict, Optional, Tuple


# Environment variable names
ENV_AUTO_RESCUE_COOLING = 'AI_SWARM_AUTO_RESCUE_COOLING'
ENV_AUTO_RESCUE_DRY_RUN = 'AI_SWARM_AUTO_RESCUE_DRY_RUN'

# Default cooling time in seconds
DEFAULT_COOLING_TIME = 30.0


# =====================================
# Pattern Classification (strict priority)
# =====================================

# AUTO_ENTER_PATTERNS: Safe to auto-send Enter (press enter only)
# Priority: Highest for auto-rescue category
AUTO_ENTER_PATTERNS = [
    # Press Enter / Hit Return variants (case-insensitive)
    (r'[Pp]ress [Ee]nter', 1),
    (r'[Pp]ress [Rr]eturn', 1),
    (r'[Hh]it [Ee]nter', 1),
    (r'[Hh]it [Rr]eturn', 1),
    # Chinese patterns
    (r'按回车', 1),
    (r'按回车键', 1),
    (r'回车继续', 1),
    # Press any key (also safe)
    (r'[Pp]ress any key to continue', 1),
]


# MANUAL_CONFIRM_PATTERNS: Require manual confirmation (y/n, confirm, continue)
# Priority: Second - returns manual_confirm_needed action
MANUAL_CONFIRM_PATTERNS = [
    # y/n interactive patterns
    (r'\[y[\/\]n\]', 2),
    (r'\[Y[\/\]n\]', 2),
    (r'\[y[\/\]N\]', 2),
    (r'\[Y[\/\]N\]', 2),
    (r'\(y[\/\]n\)', 2),
    (r'y or n', 2),
    (r'y\/n', 2),
    # Confirm prompts
    (r'[Cc]onfirm', 3),
    (r'[Aa]re you sure', 3),
    (r'确认', 3),
    (r'确定吗', 3),
    # Continue/Proceed prompts
    (r'[Cc]ontinue', 4),
    (r'[Pp]roceed', 4),
    (r'[Yy]es[/\s]?[Nn]o', 4),
    (r'ok to proceed', 4),
]


# DANGEROUS_PATTERNS: Block auto-rescue immediately (security blacklist)
# Priority: Highest - checked first, blocks all auto-actions
DANGEROUS_PATTERNS = [
    r'rm\s+-rf',           # Force recursive delete
    r'rm\s+-r',            # Recursive delete
    r'rm\s+-fr',           # Force recursive delete
    r'shred',              # Secure file deletion
    r'DROP\s+DATABASE',    # Database deletion
    r'DROP\s+TABLE',       # Table deletion
    r'DROP\s+INDEX',       # Index deletion
    r'TRUNCATE',           # Table truncation
]


class AutoRescuer:
    """
    Automatic rescue for interactive prompts in tmux panes.

    Responsibilities:
    1. Detect waiting prompt patterns in pane output
    2. Check dangerous operation blacklist
    3. Manage cooldown per window (prevent spam)
    4. Execute auto-confirm (send Enter key)
    5. Replace internal logic of Master._handle_pane_wait_states()

    Pattern Priority (strict):
    1. DANGEROUS - Block immediately, broadcast error
    2. AUTO_ENTER - Execute rescue if not in cooldown
    3. MANUAL_CONFIRM - Return manual_confirm_needed
    4. NONE - No action required

    Usage:
        rescuer = AutoRescuer(tmux_manager=tmux, broadcaster=broadcaster)
        should_rescue, action, pattern = rescuer.check_and_rescue(
            pane_output=content,
            window_name='worker-01',
            session_name='swarm-cluster-1'
        )
    """

    def __init__(
        self,
        tmux_manager: Optional[object] = None,
        cooling_time: Optional[float] = None,
        broadcaster: Optional[object] = None,
        dry_run: Optional[bool] = None
    ):
        """
        Initialize AutoRescuer.

        Args:
            tmux_manager: Tmux operation manager (for send-keys)
            cooling_time: Cooldown seconds per window (default 30s)
            broadcaster: StatusBroadcaster instance for logging
            dry_run: Dry-run mode (no actual send-keys)
        """
        # Load environment variables with defaults
        if cooling_time is None:
            cooling_time_str = os.environ.get(ENV_AUTO_RESCUE_COOLING)
            if cooling_time_str:
                try:
                    cooling_time = float(cooling_time_str)
                except ValueError:
                    cooling_time = DEFAULT_COOLING_TIME
            else:
                cooling_time = DEFAULT_COOLING_TIME

        if dry_run is None:
            dry_run = os.environ.get(ENV_AUTO_RESCUE_DRY_RUN, '').lower() in ('1', 'true', 'yes')

        self.tmux = tmux_manager
        self.cooling_time = cooling_time
        self.dry_run = dry_run

        # Use provided broadcaster or create default
        if broadcaster is not None:
            self.broadcaster = broadcaster
        else:
            from swarm.status_broadcaster import StatusBroadcaster
            self.broadcaster = StatusBroadcaster(worker_id='master')

        # Per-window cooldown tracking {window_name: last_rescue_timestamp}
        self._cooldown: Dict[str, float] = {}

        # Statistics tracking
        self._stats = {
            'total_checks': 0,
            'total_rescues': 0,
            'manual_confirms': 0,
            'dangerous_blocked': 0,
            'cooldown_skipped': 0,
        }

    def check_and_rescue(
        self,
        pane_output: str,
        window_name: str,
        session_name: str
    ) -> Tuple[bool, str, str]:
        """
        Check pane output and execute auto-rescue if needed.

        This method:
        1. Checks for empty content
        2. Detects dangerous patterns (blocks all actions)
        3. Detects auto-enter patterns (executes rescue)
        4. Detects manual confirm patterns (returns manual_needed)
        5. Returns none if no pattern matches

        Args:
            pane_output: Text content from tmux pane
            window_name: Window name (for lookup and cooldown)
            session_name: Tmux session name

        Returns:
            Tuple of (should_rescue, action, pattern):
            - should_rescue: bool - Whether action was executed
            - action: str - 'auto_enter' | 'manual_confirm' | 'dangerous_blocked' | 'cooldown' | 'rescue_failed' | 'none'
            - pattern: str - Detected pattern text, or '' if none
        """
        self._stats['total_checks'] += 1

        # Step 0: Empty content check
        if not pane_output or not pane_output.strip():
            return False, 'none', ''

        # Step 1: Dangerous pattern detection (highest priority - block immediately)
        dangerous_match = self._match_dangerous(pane_output)
        if dangerous_match:
            self._stats['dangerous_blocked'] += 1
            self.broadcaster.broadcast_error(
                task_id='',
                message=f'Dangerous pattern detected in {window_name}, blocking auto-rescue',
                meta={'window_name': window_name, 'action': 'blocked', 'pattern': dangerous_match}
            )
            return False, 'dangerous_blocked', dangerous_match

        # Step 2: Auto-enter pattern detection (executes rescue)
        auto_pattern = self._detect_pattern(pane_output, AUTO_ENTER_PATTERNS)
        if auto_pattern:
            if self._is_in_cooldown(window_name):
                self._stats['cooldown_skipped'] += 1
                return False, 'cooldown', auto_pattern

            success = self._execute_rescue(window_name, session_name)
            if success:
                self._update_cooldown(window_name)
                self._stats['total_rescues'] += 1
                self.broadcaster.broadcast_status(
                    worker_id='master',
                    task_id='',
                    state='RUNNING',
                    message=f'Auto-rescued {window_name}: detected "{auto_pattern}"'
                )
                return True, 'auto_enter', auto_pattern
            return False, 'rescue_failed', auto_pattern

        # Step 3: Manual confirm pattern detection (returns manual_needed)
        manual_pattern = self._detect_pattern(pane_output, MANUAL_CONFIRM_PATTERNS)
        if manual_pattern:
            self._stats['manual_confirms'] += 1
            self.broadcaster.broadcast_status(
                worker_id='master',
                task_id='',
                state='WAIT',
                message=f'Manual confirm needed {window_name}: "{manual_pattern}"'
            )
            return False, 'manual_confirm_needed', manual_pattern

        # Step 4: No pattern matched
        return False, 'none', ''

    def _is_dangerous(self, content: str) -> bool:
        """
        Check if content contains dangerous patterns.

        Args:
            content: Text to check

        Returns:
            True if dangerous pattern detected
        """
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        return False

    def _match_dangerous(self, content: str) -> str:
        """
        Return the matched dangerous pattern text.

        Args:
            content: Text to check

        Returns:
            Matched pattern string, or '' if no match
        """
        for pattern in DANGEROUS_PATTERNS:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(0)
        return ''

    def _detect_pattern(self, content: str, pattern_list: list) -> Optional[str]:
        """
        Detect first matching pattern from a pattern list.

        Args:
            content: Text to check
            pattern_list: List of (regex_pattern, priority) tuples

        Returns:
            Matched text string, or None if no match
        """
        for pattern, _ in pattern_list:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(0)
        return None

    def _is_in_cooldown(self, window_name: str) -> bool:
        """
        Check if window is in cooldown period.

        Args:
            window_name: Window identifier

        Returns:
            True if within cooldown window
        """
        now = time.time()
        last_time = self._cooldown.get(window_name, 0)
        return (now - last_time) < self.cooling_time

    def _update_cooldown(self, window_name: str) -> None:
        """
        Update cooldown timestamp for window.

        Args:
            window_name: Window identifier
        """
        self._cooldown[window_name] = time.time()

    def _execute_rescue(self, window_name: str, session_name: str) -> bool:
        """
        Execute auto-rescue by sending Enter key to window.

        Args:
            window_name: Window name to send Enter
            session_name: Tmux session name

        Returns:
            True if successful, False otherwise
        """
        if self.dry_run:
            print(f'[AutoRescuer] [DRY-RUN] Would send Enter to {window_name}')
            return True

        if not self.tmux:
            return False

        try:
            # Find window by name and send keys
            windows = self.tmux.list_windows(session_name)
            for w in windows:
                if w['name'] == window_name:
                    self.tmux.send_keys_to_window(session_name, w['index'], '')
                    return True
            return False
        except Exception:
            return False

    def get_stats(self) -> Dict[str, int]:
        """
        Get rescue operation statistics.

        Returns:
            Dict with: total_checks, total_rescues, manual_confirms,
                       dangerous_blocked, cooldown_skipped
        """
        return self._stats.copy()

    def reset_stats(self) -> None:
        """Reset all statistics counters."""
        self._stats = {
            'total_checks': 0,
            'total_rescues': 0,
            'manual_confirms': 0,
            'dangerous_blocked': 0,
            'cooldown_skipped': 0,
        }

    def get_cooldown_time(self, window_name: str) -> float:
        """
        Get remaining cooldown time for a window.

        Args:
            window_name: Window identifier

        Returns:
            Seconds remaining in cooldown, 0 if not in cooldown
        """
        now = time.time()
        last_time = self._cooldown.get(window_name, 0)
        elapsed = now - last_time
        return max(0, self.cooling_time - elapsed)
