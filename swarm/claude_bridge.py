#!/usr/bin/env python3
"""
Claude Bridge - Monitor master window for task input.

Monitors Claude Code's master window via tmux capture-pane,
parses task commands, and writes to FIFO for master dispatch.

IMPORTANT: AI_SWARM_BRIDGE_WINDOW or AI_SWARM_BRIDGE_PANE must point to
the window/pane running Claude Code (where you type /task commands).
Do NOT point to the window running "python3 -m swarm.cli master" -
send-keys would inject keystrokes into the master process input.

Environment:
    AI_SWARM_BRIDGE_SESSION    tmux session name (default: swarm-claude-default)
    AI_SWARM_BRIDGE_WINDOW     tmux window running Claude Code (default: codex-master)
    AI_SWARM_BRIDGE_PANE       tmux pane_id (highest priority, must be Claude Code pane)
    AI_SWARM_DIR               swarm state dir (default: /tmp/ai_swarm)
    AI_SWARM_BRIDGE_POLL_INTERVAL  poll interval (default: 1.0)
    AI_SWARM_BRIDGE_LINES      capture-pane lines (default: 200)
    AI_SWARM_INTERACTIVE       must be "1" to run
"""

import os
import sys
import time
import hashlib
import json
import signal
import re
import subprocess
from typing import Optional, Tuple

# 复用现有 FIFO 写入函数
from swarm.fifo_input import (
    get_fifo_path,
    write_to_fifo_nonblocking,
    get_interactive_mode
)


class LineFilter:
    """
    Line filter to ignore Bridge output and Claude echo.

    Filters out:
    - Bridge's own output lines (containing [Bridge], [FIFO], [DISPATCHED])
    - Claude echo patterns (Sure, I'll, Here's, etc.)

    This prevents interference from previous dispatch confirmations and
    Claude's own output patterns.
    """

    # Patterns for Bridge's own output (must be ignored)
    BRIDGE_PATTERNS = [
        r'\[Bridge\]',           # Bridge logging
        r'\[FIFO\]',             # FIFO logging
        r'\[DISPATCHED\]',       # Dispatch confirmation
        r'-> FIFO:',             # FIFO write confirmation
    ]

    # Patterns for Claude echo (must be ignored)
    CLAUDE_ECHO_PATTERNS = [
        r'^Sure,?\s*I will',
        r"^I'll\s+",
        r"^Here's",
        r'^Here’s',
        r'^\[.*\]',             # Claude markers like [THINKING]
        r'^{.*}$',               # JSON-like output
        r'^Thinking\.\.\.',
        r'^Analyzing\.\.\.',
    ]

    def __init__(self):
        """Initialize filter with compiled regex patterns."""
        import re

        # Compile patterns for efficiency
        self._bridge_patterns = [
            re.compile(p) for p in self.BRIDGE_PATTERNS
        ]
        self._claude_patterns = [
            re.compile(p) for p in self.CLAUDE_ECHO_PATTERNS
        ]

    def should_ignore(self, line: str) -> bool:
        """
        Check if a line should be ignored.

        Args:
            line: Single line from capture-pane output

        Returns:
            True if line should be ignored (Bridge output or Claude echo)
        """
        # Check Bridge patterns first (most common)
        for pattern in self._bridge_patterns:
            if pattern.search(line):
                return True

        # Check Claude echo patterns
        for pattern in self._claude_patterns:
            if pattern.search(line):
                return True

        return False


class DedupeState:
    """
    Deduplication state management: task hash + sliding window.

    Does NOT rely on line numbers (capture-pane scrolling causes instability).
    Strategy:
    - Maintain a sliding window of task hashes (size based on capture_lines)
    - Check hash cache before sending new task
    - Update cache on send, auto-evict old entries

    Cache size is dynamically set to max(100, capture_lines * 2) to ensure
    all tasks within the capture window are remembered.
    """

    DEFAULT_CACHE_SIZE = 100

    def __init__(self, state_file: str, cache_size: int = None):
        """
        Initialize deduplication state.

        Args:
            state_file: Path to save deduplication state
            cache_size: Override cache size (default: max(100, capture_lines * 2))
        """
        self.state_file = state_file
        # If cache_size provided, use it directly; otherwise calculate from capture_lines
        if cache_size is not None:
            self.cache_size = cache_size
        else:
            # Cache size is max of DEFAULT_CACHE_SIZE (100) or capture_lines * 2
            # This ensures all tasks in the capture window are remembered
            self.cache_size = max(self.DEFAULT_CACHE_SIZE, 200 * 2)
        self._load()

    def _load(self):
        """Load state from file"""
        self.task_hashes = []  # Ordered list of hashes

        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    self.task_hashes = data.get("task_hashes", [])
                    # If old state file without cache_size, keep current cache_size
                    if "cache_size" in data:
                        self.cache_size = data["cache_size"]
            except (json.JSONDecodeError, IOError):
                pass

    def _save(self):
        """Save state to file"""
        try:
            # Keep only cache_size entries
            hashes = self.task_hashes[-self.cache_size:]
            with open(self.state_file, 'w') as f:
                json.dump({"task_hashes": hashes, "cache_size": self.cache_size}, f)
        except IOError as e:
            sys.stderr.write(f"[Bridge] Failed to save dedupe state: {e}\n")

    def is_duplicate(self, task_content: str) -> Tuple[bool, str]:
        """
        Check if task is a duplicate.

        Args:
            task_content: Task prompt text

        Returns:
            (is_duplicate, hash_id)
        """
        task_hash = hashlib.md5(task_content.encode()).hexdigest()[:16]

        if task_hash in self.task_hashes:
            return True, task_hash

        return False, task_hash

    def mark_seen(self, task_hash: str):
        """Mark task as seen"""
        self.task_hashes.append(task_hash)
        # Auto-evict old entries based on dynamic cache_size
        if len(self.task_hashes) > self.cache_size:
            self.task_hashes = self.task_hashes[-self.cache_size:]
        self._save()


class TaskParser:
    """
    Task command parser.

    Only matches lines starting with /task or TASK: (case-sensitive prefix).
    Uses LineFilter to ignore Bridge output and Claude echo.

    Supported formats:
    - /task <prompt>       Standard format (must start with /task)
    - TASK: <prompt>       Colon format (must start with TASK:)
    """

    PATTERN_TASK = re.compile(r'^\s*/task\s+(.+)$')
    PATTERN_TASK_COLON = re.compile(r'^\s*TASK:\s*(.+)$')

    def __init__(self):
        """Initialize parser with line filter."""
        self.filter = LineFilter()

    def parse(self, line: str) -> Optional[str]:
        """
        Parse line and return task content or None.

        Note: Strictly matches line start, excludes Claude echo and Bridge output.

        Args:
            line: Line from capture-pane output

        Returns:
            Task prompt (stripped) or None if not a task command
        """
        # First, check if line should be ignored (Bridge output or Claude echo)
        if self.filter.should_ignore(line):
            return None

        # Must start with /task or TASK: (after stripping leading whitespace)
        stripped = line.lstrip()
        if not (stripped.startswith('/task') or stripped.startswith('TASK:')):
            return None

        # Match /task <prompt>
        match = self.PATTERN_TASK.match(line)
        if match:
            return match.group(1).strip()

        # Match TASK: <prompt>
        match = self.PATTERN_TASK_COLON.match(line)
        if match:
            return match.group(1).strip()

        return None


class ClaudeBridge:
    """
    Claude Master Window Bridge.

    Main loop:
    1. capture-pane to get window content
    2. Parse lines for /task or TASK: commands
    3. Deduplication check
    4. Write to FIFO
    """

    def __init__(self):
        self.running = True

        # Configuration
        self.session = os.environ.get('AI_SWARM_BRIDGE_SESSION', 'swarm-claude-default')
        self.window = os.environ.get('AI_SWARM_BRIDGE_WINDOW', 'codex-master')
        self.pane_id = os.environ.get('AI_SWARM_BRIDGE_PANE')  # Highest priority
        self.poll_interval = float(os.environ.get(
            'AI_SWARM_BRIDGE_POLL_INTERVAL', '1.0'))
        self.capture_lines = int(os.environ.get('AI_SWARM_BRIDGE_LINES', '200'))
        self.ai_swarm_dir = os.environ.get('AI_SWARM_DIR', '/tmp/ai_swarm')
        self.fifo_path = os.path.join(self.ai_swarm_dir, 'master_inbox')

        # Components
        self.parser = TaskParser()
        dedupe_file = os.path.join(self.ai_swarm_dir, 'bridge_dedupe.json')
        # Cache size: max(100, capture_lines * 2) to ensure all tasks in capture window are remembered
        dedupe_cache_size = max(100, self.capture_lines * 2)
        self.dedupe = DedupeState(dedupe_file, cache_size=dedupe_cache_size)

        # FIFO write failure throttling
        self._last_fifo_error_time = 0.0
        self._fifo_error_cooldown = 10.0  # 10 second cooldown

        # Status broadcaster (lazy load)
        self._broadcaster = None
        self._broadcaster_init_failed = False

        # Signal handlers
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

    def _get_pane_spec(self) -> str:
        """Get tmux pane specification"""
        if self.pane_id:
            return self.pane_id
        return f"{self.session}:{self.window}"

    def _get_pane_count(self) -> int:
        """
        Get the number of panes in the target window.

        Returns:
            Number of panes, or 0 on error
        """
        pane_spec = f"{self.session}:{self.window}"
        try:
            result = subprocess.run(
                ['tmux', 'list-panes', '-t', pane_spec, '-F', '#{pane_id}'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Count non-empty lines (each line is a pane index)
                panes = [line for line in result.stdout.strip().split('\n') if line]
                return len(panes)
        except Exception:
            pass
        return 0

    def _check_pane_config(self) -> bool:
        """
        Check pane configuration when window has multiple panes.

        If AI_SWARM_BRIDGE_PANE is not set and window has >1 pane,
        exit with error and instructions.

        Returns:
            True if config is valid, False if should exit
        """
        if self.pane_id:
            return True  # Already configured

        pane_count = self._get_pane_count()
        if pane_count > 1:
            sys.stderr.write(
                "[Bridge] ERROR: Target window has multiple panes but "
                "AI_SWARM_BRIDGE_PANE is not set.\n"
            )
            sys.stderr.write(
                "[Bridge] Set the environment variable: "
                "export AI_SWARM_BRIDGE_PANE=<pane_id>\n"
            )
            sys.stderr.write(
                "[Bridge] Find pane ID with: tmux list-panes -t "
                f"{self.session}:{self.window}\n"
            )
            return False
        return True

    def _get_broadcaster(self):
        """Lazy-load StatusBroadcaster"""
        from swarm.status_broadcaster import StatusBroadcaster

        if self._broadcaster is None and not self._broadcaster_init_failed:
            try:
                self._broadcaster = StatusBroadcaster(worker_id='bridge')
            except Exception:
                self._broadcaster_init_failed = True
        return self._broadcaster if not self._broadcaster_init_failed else None

    def _send_keys(self, text: str) -> bool:
        """
        Send text to master window via tmux send-keys.

        This provides visual feedback to Claude Code in the master window
        confirming the task has been dispatched.

        Uses literal mode (-l) to avoid character escaping issues.

        Args:
            text: Text to send

        Returns:
            True on success, False on error
        """
        pane_spec = self._get_pane_spec()

        try:
            # Use literal mode (-l) to avoid escaping issues
            subprocess.run(
                ['tmux', 'send-keys', '-l', '-t', pane_spec, text, 'Enter'],
                capture_output=True,
                timeout=5
            )
            return True
        except subprocess.TimeoutExpired:
            sys.stderr.write("[Bridge] send-keys timeout\n")
            return False
        except FileNotFoundError:
            sys.stderr.write("[Bridge] tmux not found for send-keys\n")
            return False
        except Exception as e:
            sys.stderr.write(f"[Bridge] send-keys error: {e}\n")
            return False

    def _capture_pane(self) -> str:
        """Use tmux capture-pane to get window content"""
        pane_spec = self._get_pane_spec()

        try:
            result = subprocess.run(
                ['tmux', 'capture-pane', '-t', pane_spec, '-p',
                 '-S', f'-{self.capture_lines}'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout
        except subprocess.TimeoutExpired:
            sys.stderr.write("[Bridge] capture-pane timeout\n")
            return ""
        except FileNotFoundError:
            sys.stderr.write("[Bridge] tmux not found\n")
            return ""
        except Exception as e:
            sys.stderr.write(f"[Bridge] capture-pane error: {e}\n")
            return ""

    def _write_to_fifo(self, task: str) -> bool:
        """
        Write to FIFO and send dispatch confirmation via send-keys.

        Args:
            task: Task prompt to write

        Returns:
            True on success, False if no reader
        """
        success = write_to_fifo_nonblocking(self.fifo_path, task)

        now = time.time()
        if success:
            # Send dispatch confirmation to master window via send-keys
            dispatch_msg = f"[DISPATCHED] {task[:60]}"
            self._send_keys(dispatch_msg)

            sys.stdout.write(f"[Bridge] -> FIFO: {task[:60]}...\n")
            sys.stdout.flush()

            # Broadcast dispatched status
            self._log_status("dispatched", task=task[:100], method="fifo+send-keys")
        else:
            # Throttling: avoid repeated spam
            if now - self._last_fifo_error_time >= self._fifo_error_cooldown:
                sys.stderr.write("[Bridge] FIFO write failed (no reader), will retry...\n")
                self._last_fifo_error_time = now
                self._log_status("fifo_no_reader")

        return success

    def _log_status(self, status: str, **extra):
        """
        Write status log.

        - bridge.log: Plain text (for debugging)
        - status.log: JSONL format (reuses StatusBroadcaster)

        Note: HELP state is used for Bridge events (including dispatched),
        meta.type=BRIDGE clearly distinguishes from task states.
        meta.bridge_status indicates the specific event type.
        """
        from swarm.status_broadcaster import BroadcastState

        ts = time.strftime('%Y-%m-%d %H:%M:%S')

        # 1. Write bridge.log (ensure directory exists)
        try:
            os.makedirs(self.ai_swarm_dir, exist_ok=True)
            log_file = os.path.join(self.ai_swarm_dir, 'bridge.log')
            with open(log_file, 'a') as f:
                f.write(f"[{ts}] {status}\n")
        except IOError:
            pass

        # 2. Write status.log (reuses StatusBroadcaster, HELP + meta.type=BRIDGE)
        # Note: HELP state indicates Bridge non-task events, not actual tasks
        bc = self._get_broadcaster()
        if bc:
            try:
                bc.broadcast(
                    state=BroadcastState.HELP,
                    task_id="",
                    message=status,
                    meta={"type": "BRIDGE", "bridge_status": status, **extra}
                )
            except Exception:
                pass  # Broadcaster may be unavailable

    def _process_capture(self, capture: str) -> int:
        """
        Process captured pane content.

        Args:
            capture: Raw capture-pane output

        Returns:
            Number of tasks sent to FIFO
        """
        if not capture:
            return 0

        tasks_sent = 0
        for line in capture.split('\n'):
            task = self.parser.parse(line)
            if not task:
                continue

            # Deduplication check
            is_dup, task_hash = self.dedupe.is_duplicate(task)
            if is_dup:
                self._log_status("skipped_duplicate", task_hash=task_hash)
                continue

            # Write to FIFO
            if self._write_to_fifo(task):
                self.dedupe.mark_seen(task_hash)
                self._log_status("task_sent", task_hash=task_hash)
                tasks_sent += 1

        return tasks_sent

    def run(self):
        """Main loop"""
        if not get_interactive_mode():
            sys.stderr.write("[Bridge] AI_SWARM_INTERACTIVE=1 required\n")
            return 1

        # Check pane configuration for multi-pane windows
        if not self._check_pane_config():
            return 2

        pane_spec = self._get_pane_spec()
        sys.stdout.write(
            f"[Bridge] Starting bridge (session={self.session}, "
            f"pane={pane_spec}, lines={self.capture_lines}, "
            f"poll={self.poll_interval}s)\n"
        )
        sys.stdout.flush()
        self._log_status("started", pane=pane_spec, lines=self.capture_lines)

        while self.running:
            try:
                # Capture window content
                capture = self._capture_pane()

                if capture:
                    self._process_capture(capture)

            except Exception as e:
                sys.stderr.write(f"[Bridge] Error: {e}\n")
                self._log_status("error", error=str(e))

            time.sleep(self.poll_interval)

        sys.stdout.write("[Bridge] Stopped\n")
        self._log_status("stopped")
        return 0

    def _shutdown(self, signum, frame):
        """Signal handler"""
        sys.stdout.write(f"\n[Bridge] Received signal {signum}, shutting down...\n")
        self.running = False


def main():
    """Entry point"""
    bridge = ClaudeBridge()
    return bridge.run()


if __name__ == '__main__':
    sys.exit(main())
