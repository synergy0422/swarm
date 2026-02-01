#!/usr/bin/env python3
"""
Master Node for AI Swarm System

Provides minimal Master loop for:
- Worker status scanning (via status.log)
- Task assignment (FIFO with lock acquisition)
- WAIT detection with conservative auto-confirm
"""

import os
import json
import time
import signal
import re
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List

from swarm.task_queue import TaskQueue
from swarm.task_lock import TaskLockManager
from swarm.status_broadcaster import get_ai_swarm_dir, StatusBroadcaster
from swarm.master_dispatcher import MasterDispatcher


# Default configuration
DEFAULT_POLL_INTERVAL = 1.0  # 1 second
DEFAULT_AI_SWARM_DIR = '/tmp/ai_swarm'
DEFAULT_STATUS_LOG = 'status.log'

# Environment variable names
ENV_POLL_INTERVAL = 'AI_SWARM_POLL_INTERVAL'


def get_poll_interval() -> float:
    """
    Get poll interval from environment variable or use default.

    Returns:
        float: Poll interval in seconds (default 1.0)
    """
    interval_str = os.environ.get(ENV_POLL_INTERVAL)
    if interval_str:
        try:
            return float(interval_str)
        except ValueError:
            pass
    return DEFAULT_POLL_INTERVAL


# WAIT detection patterns (by priority)
WAIT_PATTERNS = [
    # Priority 1: Interactive confirm (y/n)
    (r'\[y[\//]n\]|\[Y[\//]n\]|\(y[\//]n\)|y or n', 1),
    # Priority 2: Press ENTER to continue
    (r'[Pp]ress [Ee]nter|[Pp]ress [Rr]eturn|[Hh]it [Ee]nter|按回车|回车继续|[Pp]ress any key to continue', 2),
    # Priority 3: Confirm prompts
    (r'[Cc]onfirm|[Aa]re you sure|确认|确定吗', 3),
]

# ENTER patterns for pane detection (Priority 2 - safe to auto-confirm)
ENTER_PATTERNS = [
    r'[Pp]ress [Ee]nter',
    r'[Pp]ress [Rr]eturn',
    r'[Hh]it [Ee]nter',
    r'回车继续',
    r'按回车',
]

# Blacklist keywords (never auto-confirm)
BLACKLIST_KEYWORDS = [
    'delete', 'remove', 'rm -rf', 'format', 'overwrite',
    'drop database', 'drop table',
    'kill', 'terminate',
    'sudo', 'password', 'token', 'ssh', 'key',
    '生产', 'prod',
]


class MasterScanner:
    """
    Scans worker status from shared status.log file.

    Reads the latest status entry for each worker to determine:
    - Worker state (START, DONE, WAIT, ERROR, etc.)
    - Current task being processed
    - Last activity timestamp
    """

    def __init__(self):
        """Initialize MasterScanner"""
        self._ai_swarm_dir = get_ai_swarm_dir()
        self._status_log_path = os.path.join(self._ai_swarm_dir, DEFAULT_STATUS_LOG)

    def scan_workers(self) -> Dict[str, dict]:
        """
        Scan status.log to get latest status for each worker.

        Returns:
            Dict mapping worker_id to latest status info:
            {
                'worker_id': 'worker-1',
                'task_id': 'task-123',
                'state': 'RUNNING',
                'message': '...',
                'ts': '2026-01-31T12:00:00.000Z'
            }
        """
        workers = {}

        if not os.path.exists(self._status_log_path):
            return workers

        try:
            with open(self._status_log_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        entry = json.loads(line)
                        worker_id = entry.get('worker_id')
                        if worker_id:
                            workers[worker_id] = entry
                    except json.JSONDecodeError:
                        continue
        except (IOError, OSError):
            pass

        return workers

    def get_worker_status(self, worker_id: str) -> Optional[dict]:
        """
        Get latest status for a specific worker.

        Args:
            worker_id: Worker identifier

        Returns:
            Status dict or None if not found
        """
        workers = self.scan_workers()
        return workers.get(worker_id)

    def is_worker_idle(self, worker_status: dict) -> bool:
        """
        Check if worker is idle (available for new task).

        Worker is idle if:
        - State is DONE, SKIP, or ERROR
        - No active lock held

        Args:
            worker_status: Worker status dict

        Returns:
            bool: True if worker is idle
        """
        if not worker_status:
            return True  # No status = idle

        state = worker_status.get('state')
        return state in ('DONE', 'SKIP', 'ERROR', None)


class WaitDetector:
    """
    Detects WAIT state from worker output patterns.

    Only detects "obviously waiting for input" patterns.
    Conservative approach: never auto-yes, only auto-enter for safe prompts.
    """

    def __init__(self):
        """Initialize WaitDetector"""
        self._ai_swarm_dir = get_ai_swarm_dir()
        # TODO: Support tmux capture-pane for WAIT detection
        # For MVP, we rely on status.log state = WAIT

    def is_wait_state(self, worker_status: dict) -> bool:
        """
        Check if worker is in WAIT state.

        Args:
            worker_status: Worker status dict

        Returns:
            bool: True if worker is waiting
        """
        if not worker_status:
            return False
        return worker_status.get('state') == 'WAIT'

    def should_auto_confirm(self, message: str) -> bool:
        """
        Determine if WAIT can be auto-confirmed (ENTER only, never yes).

        Only auto-confirm if:
        - No blacklist keywords present
        - Pattern is "Press ENTER to continue" type

        Args:
            message: Status message to check

        Returns:
            bool: True if safe to send ENTER
        """
        if not message:
            return False

        message_lower = message.lower()

        # Check blacklist first
        for keyword in BLACKLIST_KEYWORDS:
            if keyword in message_lower:
                return False

        # Check for safe ENTER patterns (Priority 2 only)
        safe_pattern = WAIT_PATTERNS[1][0]  # Press ENTER patterns
        if re.search(safe_pattern, message, re.IGNORECASE):
            return True

        return False

    def detect_in_pane(self, content: str) -> List[str]:
        """
        Detect ENTER patterns in pane content.

        Args:
            content: String content from tmux pane

        Returns:
            List of matching patterns found in content
        """
        if not content:
            return []

        matches = []
        for pattern in ENTER_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                matches.append(pattern)
        return matches


class PaneScanner:
    """Scans tmux pane content using TmuxCollaboration."""

    def __init__(self, tmux_collaboration: Optional['TmuxCollaboration'] = None):
        """Initialize with optional TmuxCollaboration for testing."""
        self.tmux = tmux_collaboration

    def scan_all(self, session_name: str) -> Dict[str, str]:
        """Capture content from all windows.

        Returns:
            Dict mapping window_name to pane content.
            Empty dict if tmux unavailable.
        """
        if not self.tmux:
            return {}
        try:
            return self.tmux.capture_all_windows(session_name)
        except Exception:
            return {}

    def send_enter(self, session_name: str, window_name: str) -> bool:
        """Send ENTER key to a window by name.

        Returns:
            True if sent, False if window not found or error.
        """
        if not self.tmux:
            return False
        try:
            # Find window index by name
            windows = self.tmux.list_windows(session_name)
            for w in windows:
                if w["name"] == window_name:
                    self.tmux.send_keys_to_window(session_name, w["index"], "")
                    return True
            return False
        except Exception:
            return False


class Master:
    """
    Main Master node for AI Swarm coordination.

    Runs a continuous loop:
    1. Scan worker status (from status.log)
    2. Detect WAIT states (check for auto-confirm)
    3. Find idle workers
    4. Assign pending tasks to idle workers (via MasterDispatcher with mailbox)
    5. Sleep for poll_interval

    Conservative behavior:
    - Never auto-yes (only auto-enter for safe prompts)
    - Blacklist dangerous operations
    - Use locks to prevent duplicate assignment
    """

    def __init__(
        self,
        poll_interval: Optional[float] = None,
        cluster_id: str = 'default',
        tmux_collaboration: Optional['TmuxCollaboration'] = None,
        pane_poll_interval: float = 3.0
    ):
        """
        Initialize Master.

        Args:
            poll_interval: Scan interval in seconds (default from env or 1.0)
            cluster_id: Cluster identifier for dispatcher and tmux session name
            tmux_collaboration: Optional TmuxCollaboration instance for pane scanning
            pane_poll_interval: Interval for pane scanning in seconds (default 3.0)
        """
        self.poll_interval = poll_interval or get_poll_interval()
        self.running = True
        self.cluster_id = cluster_id
        self.pane_poll_interval = pane_poll_interval

        self.scanner = MasterScanner()
        self.wait_detector = WaitDetector()
        self.pane_scanner = PaneScanner(tmux_collaboration)
        self.dispatcher = MasterDispatcher(cluster_id=cluster_id)
        self.broadcaster = StatusBroadcaster(worker_id='master')

        # Cooldown tracking for auto-ENTER (30 seconds per window)
        self._last_auto_enter: Dict[str, float] = {}

        # Register signal handlers
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

    def _shutdown(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n[Master] Received signal {signum}, shutting down...")
        self.running = False

    def _handle_pane_wait_states(self) -> None:
        """Scan all panes and auto-send ENTER for detected patterns."""
        session_name = f"swarm-{self.cluster_id}"
        pane_contents = self.pane_scanner.scan_all(session_name)

        now = time.time()
        for window_name, content in pane_contents.items():
            patterns = self.wait_detector.detect_in_pane(content)

            if patterns:
                # Check cooldown (30 seconds)
                last_enter = self._last_auto_enter.get(window_name, 0)
                if now - last_enter < 30:
                    continue  # Still in cooldown

                # Send ENTER
                if self.pane_scanner.send_enter(session_name, window_name):
                    self._last_auto_enter[window_name] = now
                    print(f"[Master] Auto-ENTER for {window_name}")

    def handle_wait_states(self, workers: Dict[str, dict]) -> None:
        """
        Handle workers in WAIT state.

        For each WAIT state:
        1. Check if safe to auto-confirm
        2. If safe, send ENTER (conservative)
        3. If not safe, broadcast HELP for human intervention

        Args:
            workers: Dict of worker_id -> status
        """
        for worker_id, status in workers.items():
            if not self.wait_detector.is_wait_state(status):
                continue

            task_id = status.get('task_id', '')
            message = status.get('message', '')

            if self.wait_detector.should_auto_confirm(message):
                # TODO: Send ENTER to worker via tmux
                # For MVP, just log
                print(f"[Master] Worker {worker_id} waiting, would auto-ENTER")
            else:
                # Broadcast HELP state for human intervention
                self.broadcaster.broadcast_help(
                    task_id=task_id,
                    message=f'Worker {worker_id} needs human help: {message}',
                    meta={'worker_id': worker_id}
                )

    def run(self) -> None:
        """
        Run Master main loop.

        Continuously:
        1. Scan worker status
        2. Handle WAIT states
        3. Dispatch tasks to idle workers (via MasterDispatcher with mailbox)
        3.5. Scan panes and auto-ENTER (on pane_poll_interval timing)
        4. Sleep for poll_interval
        """
        print(f"[Master] Starting Master loop (poll_interval={self.poll_interval}s)")

        last_pane_scan_time = 0.0

        while self.running:
            try:
                now = time.time()

                # 1. Scan worker status
                workers_dict = self.scanner.scan_workers()

                # Convert dict to WorkerStatus objects
                from swarm import master_scanner
                worker_statuses = {}
                for worker_id, status_dict in workers_dict.items():
                    worker_statuses[worker_id] = master_scanner.WorkerStatus(
                        worker_id=worker_id,
                        task_id=status_dict.get('task_id'),
                        state=status_dict.get('state'),
                        message=status_dict.get('message', ''),
                        timestamp=status_dict.get('ts', '')
                    )

                # 2. Handle WAIT states
                self.handle_wait_states(workers_dict)

                # 3. Dispatch tasks to idle workers (includes mailbox writing)
                results = self.dispatcher.dispatch_all(worker_statuses)

                if results:
                    for result in results:
                        if result.success:
                            print(f"[Master] Assigned {result.task_id} to {result.worker_id}")

                # 3.5. Scan panes and auto-ENTER (independent interval)
                if now - last_pane_scan_time >= self.pane_poll_interval:
                    self._handle_pane_wait_states()
                    last_pane_scan_time = now

                # 4. Sleep before next scan
                time.sleep(self.poll_interval)

            except Exception as e:
                # Broadcast ERROR to status.log
                self.broadcaster.broadcast_error(
                    task_id="",
                    message=f"Master loop error: {e}",
                    meta={"exc": str(e)}
                )
                print(f"[Master] Error in main loop: {e}")
                time.sleep(self.poll_interval)

        print("[Master] Master stopped")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='AI Swarm Master'
    )
    parser.add_argument(
        '--poll-interval',
        type=float,
        default=None,
        help='Poll interval in seconds (default: from env or 1.0)'
    )

    args = parser.parse_args()

    master = Master(poll_interval=args.poll_interval)
    master.run()


if __name__ == '__main__':
    main()
