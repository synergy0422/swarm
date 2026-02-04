#!/usr/bin/env python3
"""
Master Node for AI Swarm System

Provides minimal Master loop for:
- Worker status scanning (via status.log)
- Task assignment (FIFO with lock acquisition)
- WAIT detection with conservative auto-confirm
- Auto-rescue for interactive prompts (via AutoRescuer)
- Status summary table output
"""

import os
import json
import time
import signal
import re
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Tuple

from swarm.task_queue import TaskQueue
from swarm.task_lock import TaskLockManager
from swarm.status_broadcaster import get_ai_swarm_dir, StatusBroadcaster
from swarm.master_dispatcher import MasterDispatcher
from swarm.auto_rescuer import AutoRescuer


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


# State priority for summary table (highest to lowest)
STATE_PRIORITY = {
    'ERROR': 0,
    'WAIT': 1,
    'RUNNING': 2,
    'START': 3,
    'DONE': 4,
    'SKIP': 5,
}


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


class PaneSummary:
    """
    Tracks pane state for summary table output.

    Attributes:
        window_name: Name of the tmux window
        last_state: Last detected state (ERROR, WAIT, RUNNING, DONE, IDLE)
        last_action: Last auto-rescue action taken
        task_id: Associated task ID (if any)
        note: Additional notes (pattern detected, etc.)
        last_update_ts: Unix timestamp of last state update
        wait_since_ts: Unix timestamp when entered WAIT state (None when not in WAIT)
        error_streak: Consecutive ERROR count
    """

    def __init__(self, window_name: str):
        self.window_name = window_name
        self.last_state = 'IDLE'
        self.last_action = ''
        self.task_id = '-'
        self.note = ''
        self.last_update_ts = time.time()
        self.wait_since_ts = None
        self.error_streak = 0

    def update_state(self, new_state: str, timestamp: float):
        """Update state and maintain tracking fields.

        Args:
            new_state: The new state value
            timestamp: Current timestamp from time.time()

        Behavior:
        - last_update_ts: ALWAYS updates regardless of whether state changed
          (consecutive ERROR should update timestamp to show "still failing")
        - wait_since_ts:
          - On WAIT entry: set to timestamp (if not already set)
          - On ERROR: does NOT clear wait_since_ts
          - On other non-WAIT states: set to None (cleared on exit)
        - error_streak:
          - On ERROR: increment by 1
          - On other states: reset to 0
        """
        self.last_update_ts = timestamp

        # Handle WAIT state
        if new_state == 'WAIT':
            if self.wait_since_ts is None:
                self.wait_since_ts = timestamp
        elif new_state == 'ERROR':
            # ERROR does NOT clear wait_since_ts
            pass
        else:
            # Clear wait_since_ts when leaving WAIT for other states
            self.wait_since_ts = None

        # Handle ERROR streak
        if new_state == 'ERROR':
            self.error_streak += 1
        else:
            # Reset error streak when leaving ERROR
            self.error_streak = 0

        self.last_state = new_state

    def _format_timestamp(self, ts: float) -> str:
        """Format timestamp as HH:MM:SS (local time).

        Args:
            ts: Unix timestamp

        Returns:
            Formatted time string "HH:MM:SS" in local timezone
        """
        dt = datetime.fromtimestamp(ts)
        return dt.strftime('%H:%M:%S')

    def _format_wait_duration(self, wait_ts: float, now: float) -> str:
        """Format wait duration as human-readable string.

        Args:
            wait_ts: Unix timestamp when WAIT started
            now: Current Unix timestamp

        Returns:
            Duration string like "30s", "2m", "1h" or "-" if invalid
        """
        # Check for invalid timestamps (0 or negative are not valid Unix timestamps)
        if wait_ts <= 0:
            return '-'

        duration = now - wait_ts
        if duration <= 0:
            return '-'

        if duration < 60:
            return f"{int(duration)}s"
        elif duration < 3600:
            return f"{int(duration / 60)}m"
        else:
            return f"{int(duration / 3600)}h"


class Master:
    """
    Main Master node for AI Swarm coordination.

    Runs a continuous loop:
    1. Scan worker status (from status.log)
    2. Detect WAIT states (check for auto-confirm)
    3. Find idle workers
    4. Assign pending tasks to idle workers (via MasterDispatcher with mailbox)
    5. Scan panes and auto-rescue (via AutoRescuer)
    6. Output status summary table

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
        pane_poll_interval: float = 3.0,
        dry_run: bool = False
    ):
        """
        Initialize Master.

        Args:
            poll_interval: Scan interval in seconds (default from env or 1.0)
            cluster_id: Cluster identifier for dispatcher and tmux session name
            tmux_collaboration: Optional TmuxCollaboration instance for pane scanning
            pane_poll_interval: Interval for pane scanning in seconds (default 3.0)
            dry_run: Dry-run mode for auto-rescuer (no actual send-keys)
        """
        self.poll_interval = poll_interval or get_poll_interval()
        self.running = True
        self.cluster_id = cluster_id
        self.pane_poll_interval = pane_poll_interval
        self.dry_run = dry_run
        self.session_name = f"swarm-{cluster_id}"

        self.scanner = MasterScanner()
        self.wait_detector = WaitDetector()
        self.pane_scanner = PaneScanner(tmux_collaboration)
        self.dispatcher = MasterDispatcher(cluster_id=cluster_id)
        self.broadcaster = StatusBroadcaster(worker_id='master')

        # AutoRescuer for automatic rescue of interactive prompts
        self.auto_rescuer = AutoRescuer(
            tmux_manager=self.pane_scanner.tmux if self.pane_scanner.tmux else None,
            broadcaster=self.broadcaster,
            dry_run=dry_run
        )

        # Pane summary tracking {window_name: PaneSummary}
        self._pane_summaries: Dict[str, PaneSummary] = {}

        # Register signal handlers
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

    def _shutdown(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n[Master] Received signal {signum}, shutting down...")
        self.running = False

    def _handle_pane_wait_states(self) -> None:
        """
        Scan all panes and execute auto-rescue via AutoRescuer.

        Uses AutoRescuer.check_and_rescue() which:
        1. Detects dangerous patterns (blocks)
        2. Detects auto-enter patterns (executes rescue)
        3. Detects manual confirm patterns (returns manual_needed)
        4. Manages per-window cooldown internally
        """
        pane_contents = self.pane_scanner.scan_all(self.session_name)
        now = time.time()

        for window_name, content in pane_contents.items():
            # Initialize summary if needed
            if window_name not in self._pane_summaries:
                self._pane_summaries[window_name] = PaneSummary(window_name)
            summary = self._pane_summaries[window_name]

            # Use AutoRescuer for detection and rescue
            should_rescue, action, pattern = self.auto_rescuer.check_and_rescue(
                pane_output=content,
                window_name=window_name,
                session_name=self.session_name
            )

            # Update summary based on action
            if action == 'auto_enter':
                summary.update_state('RUNNING', now)
                summary.last_action = 'AUTO_ENTER'
                summary.note = f'"{pattern}"'
            elif action == 'manual_confirm_needed':
                summary.update_state('WAIT', now)
                summary.last_action = 'MANUAL'
                summary.note = f'"{pattern}"'
            elif action == 'dangerous_blocked':
                summary.update_state('ERROR', now)
                summary.last_action = 'BLOCKED'
                summary.note = f'[DANGEROUS] {pattern}'
            elif action == 'cooldown':
                summary.last_action = 'COOLDOWN'
                remaining = self.auto_rescuer.get_cooldown_time(window_name)
                summary.note = f'Wait {remaining:.1f}s'
                # Update timestamp but don't change state
                summary.last_update_ts = now
            elif action == 'rescue_failed':
                summary.update_state('WAIT', now)
                summary.last_action = 'FAILED'
                summary.note = f'Rescue failed: "{pattern}"'
            elif action == 'blocked_by_config':
                # Config blocks auto-rescue - show as WAIT with config block note
                summary.update_state('WAIT', now)
                summary.last_action = 'BLOCKED'
                summary.note = '[BLOCKED BY CONFIG]'
            elif action == 'allowlist_missed':
                # Content doesn't match allowlist - requires manual confirm
                summary.update_state('WAIT', now)
                summary.last_action = 'ALLOWLIST'
                summary.note = '[ALLOWLIST MISSED]'
            elif action == 'disabled':
                # Auto-rescue is disabled - show as IDLE with disabled note
                summary.update_state('IDLE', now)
                summary.last_action = 'DISABLED'
                summary.note = '[AUTO-RESCUE DISABLED]'
            elif action == 'none':
                # Reset to IDLE when no patterns detected
                summary.update_state('IDLE', now)
                summary.last_action = ''
                summary.note = ''

    def handle_wait_states(self, workers: Dict[str, dict]) -> None:
        """
        Handle workers in WAIT state from status.log.

        For each WAIT state:
        1. Check if safe to auto-confirm
        2. If safe, log (pane-based rescue handles actual send)
        3. If not safe, broadcast HELP for human intervention

        Args:
            workers: Dict of worker_id -> status
        """
        for worker_id, status in workers.items():
            if not self.wait_detector.is_wait_state(status):
                continue

            task_id = status.get('task_id', '')
            message = status.get('message', '')

            # For pane-based rescue (AutoRescuer), just log
            print(f"[Master] Worker {worker_id} waiting: {message}")

    def _get_state_priority(self, state: str) -> int:
        """
        Get priority value for state sorting.

        Priority order: ERROR > WAIT > RUNNING > START > DONE > SKIP > IDLE

        Args:
            state: State string

        Returns:
            Priority value (lower = higher priority)
        """
        return STATE_PRIORITY.get(state, 99)

    def _format_summary_table(self) -> str:
        """
        Format status summary table for output.

        Format: window | state | task_id | last_update | wait_for | err | note
        Sorted by state priority (ERROR > WAIT > RUNNING > DONE/IDLE)

        Returns:
            Formatted table string
        """
        if not self._pane_summaries:
            return "No pane data available"

        # Collect summaries with priority
        summaries = list(self._pane_summaries.values())

        # Sort by state priority, then by window name
        summaries.sort(key=lambda s: (self._get_state_priority(s.last_state), s.window_name))

        # Get current time for duration calculations
        now = time.time()

        # Format output
        lines = []
        lines.append("")
        lines.append("=" * 90)
        lines.append("WINDOW         STATE    TASK_ID    LAST_UPDATE  WAIT_FOR   ERR  NOTE")
        lines.append("-" * 90)

        for summary in summaries:
            window = summary.window_name[:12].ljust(12)
            state = summary.last_state.ljust(8)
            task_id = summary.task_id.ljust(10)

            # Format last_update as HH:MM:SS
            last_update = summary._format_timestamp(summary.last_update_ts)

            # Format wait_for duration
            if summary.last_state == 'WAIT' and summary.wait_since_ts is not None:
                wait_for = summary._format_wait_duration(summary.wait_since_ts, now)
            else:
                wait_for = '-'

            # Format error streak
            if summary.last_state == 'ERROR' and summary.error_streak > 0:
                err = str(summary.error_streak)
            else:
                err = '-'

            note = summary.note if summary.note else '-'

            lines.append(f"{window} {state} {task_id} {last_update}  {wait_for:<8} {err:<3} {note}")

        lines.append("=" * 90)
        lines.append(f"Total windows: {len(summaries)}")
        lines.append("")

        return "\n".join(lines)

    def _update_summary_from_workers(self, workers: Dict[str, dict]) -> None:
        """
        Update pane summaries based on worker status.

        Uses priority-based merging: only update state if worker state has higher priority.
        Priority order: ERROR(0) > WAIT(1) > RUNNING(2) > DONE(3) > IDLE(4)

        Args:
            workers: Dict of worker_id -> status dict
        """
        now = time.time()

        for worker_id, status in workers.items():
            # Map worker_id to window_name (usually same as worker_id)
            window_name = worker_id

            if window_name not in self._pane_summaries:
                self._pane_summaries[window_name] = PaneSummary(window_name)
            summary = self._pane_summaries[window_name]

            worker_state = status.get('state', 'IDLE')
            task_id = status.get('task_id', '-')

            summary.task_id = task_id

            # Don't let stale worker ERROR/WAIT override a clean pane (IDLE)
            # This prevents race conditions when pane scan resets to IDLE but
            # worker status hasn't updated yet in the shared status.log
            if summary.last_state == 'IDLE' and worker_state in ('ERROR', 'WAIT'):
                # Pane is clean, worker hasn't updated yet - skip this update
                # Worker will update correctly in next cycle
                continue

            # Priority-based merge: only update if worker state has higher priority
            # ERROR(0) > WAIT(1) > RUNNING(2) > DONE(3) > IDLE(4)
            worker_priority = self._get_state_priority(worker_state)
            pane_priority = self._get_state_priority(summary.last_state)

            if worker_priority < pane_priority:
                summary.update_state(worker_state, now)

    def output_status_summary(self) -> None:
        """Output status summary table to stdout."""
        # Update summary table
        workers = self.scanner.scan_workers()
        self._update_summary_from_workers(workers)

        # Print summary table
        summary_table = self._format_summary_table()
        print(summary_table)

    def run(self) -> None:
        """
        Run Master main loop.

        Continuously:
        1. Scan worker status
        2. Handle WAIT states
        3. Dispatch tasks to idle workers (via MasterDispatcher with mailbox)
        4. Scan panes and auto-rescue (on pane_poll_interval timing)
        5. Output status summary table
        6. Sleep for poll_interval
        """
        print(f"[Master] Starting Master loop (poll_interval={self.poll_interval}s)")

        last_pane_scan_time = 0.0
        last_summary_time = 0.0
        summary_interval = 30.0  # Output summary every 30 seconds

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

                # 4. Scan panes and auto-rescue (independent interval)
                if now - last_pane_scan_time >= self.pane_poll_interval:
                    self._handle_pane_wait_states()
                    last_pane_scan_time = now

                # 5. Output status summary table (periodic)
                if now - last_summary_time >= summary_interval:
                    self.output_status_summary()
                    last_summary_time = now

                # 6. Sleep before next scan
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
    parser.add_argument(
        '--pane-poll-interval',
        type=float,
        default=3.0,
        help='Pane scanning interval in seconds (default: 3.0)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=False,
        help='Dry-run mode (no actual tmux send-keys)'
    )

    args = parser.parse_args()

    master = Master(
        poll_interval=args.poll_interval,
        pane_poll_interval=args.pane_poll_interval,
        dry_run=args.dry_run
    )
    master.run()


if __name__ == '__main__':
    main()
