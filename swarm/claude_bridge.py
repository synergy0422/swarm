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
    AI_SWARM_BRIDGE_WORKER_WINDOW  tmux worker window name for direct dispatch (default: workers)
    AI_SWARM_BRIDGE_WORKER_PANES   comma-separated pane ids for direct dispatch (optional)
    AI_SWARM_BRIDGE_DIRECT_FALLBACK  fallback to direct worker dispatch when FIFO has no reader (default: 1)
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
import random
import string
import threading
from typing import Optional, Tuple

# 复用现有 FIFO 写入函数
from swarm.fifo_input import (
    get_fifo_path,
    write_to_fifo_nonblocking,
    get_interactive_mode
)


class BridgePhase:
    """
    Enum for bridge dispatch phases.

    Used for structured lifecycle tracking:
    - CAPTURED: Task command captured from master pane
    - PARSED: Task command successfully parsed
    - DISPATCHED: Task sent to worker (FIFO or direct)
    - ACKED: Worker acknowledged task receipt
    - RETRY: Dispatch failed, retrying
    - FAILED: All retries exhausted, task failed
    """
    CAPTURED = "CAPTURED"
    PARSED = "PARSED"
    DISPATCHED = "DISPATCHED"
    ACKED = "ACKED"
    RETRY = "RETRY"
    FAILED = "FAILED"


class DispatchMode:
    """
    Enum for dispatch modes used by the bridge.

    - fifo: FIFO write succeeded, task queued for master
    - direct: FIFO unavailable, direct dispatch to worker used
    - direct_fallback: FIFO failed, fell back to direct dispatch
    """
    FIFO = "fifo"
    DIRECT = "direct"
    DIRECT_FALLBACK = "direct_fallback"


class BridgeDispatchError(Exception):
    """
    Exception raised when dispatch fails after all retries.

    Attributes:
        task_id: The bridge task ID that failed
        attempts: List of (worker_pane, success, latency_ms) tuples
        last_error: Error message from last attempt
    """
    def __init__(self, task_id: str, attempts: list, last_error: str = None):
        self.task_id = task_id
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(f"Dispatch failed for {task_id} after {len(attempts)} attempts: {last_error}")


class BridgeTaskIdGenerator:
    """
    Thread-safe unique task ID generator for bridge dispatch tracking.

    Generates IDs in format: br-{unix_ns}-{3-char_suffix}
    Example: br-1739999999123-abc

    Features:
    - Nanosecond timestamp for near-uniqueness
    - Random suffix for collision prevention
    - Persists recent IDs for deduplication
    - Thread-safe generation
    """

    def __init__(self, id_file: str = None):
        """
        Initialize task ID generator.

        Args:
            id_file: Path to persist recent IDs (for collision detection)
        """
        self._lock = threading.Lock()
        self._recent_ids = set()
        self._id_file = id_file

        # Load recent IDs from file if provided
        if id_file:
            try:
                os.makedirs(os.path.dirname(id_file), exist_ok=True) if os.path.dirname(id_file) else None
                if os.path.exists(id_file):
                    with open(id_file, 'r') as f:
                        self._recent_ids = set(line.strip() for line in f if line.strip())
            except (IOError, OSError):
                pass

    def _save_recent_ids(self):
        """Persist recent IDs to file."""
        if not self._id_file:
            return
        try:
            # Keep last 1000 IDs for collision detection
            with open(self._id_file, 'w') as f:
                for id_ in list(self._recent_ids)[-1000:]:
                    f.write(f"{id_}\n")
        except (IOError, OSError):
            pass

    def generate(self) -> str:
        """
        Generate a unique bridge task ID.

        Format: br-{unix_ns}-{3-char_suffix}
        Example: br-1739999999123-abc

        Returns:
            Unique bridge task ID
        """
        with self._lock:
            while True:
                # Nanosecond timestamp
                ts = int(time.time() * 1e9)

                # 3-character random suffix (167761 possibilities)
                suffix = ''.join(random.choices(
                    string.ascii_lowercase + string.digits,
                    k=3
                ))

                task_id = f"br-{ts}-{suffix}"

                # Check for collision with recent IDs
                if task_id not in self._recent_ids:
                    self._recent_ids.add(task_id)
                    self._save_recent_ids()
                    return task_id

                # Collision detected - generate new ID (extremely rare)


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

        # Normalize common terminal prompt prefixes, e.g.:
        # "❯ TASK: ...", "> /task ...", "$ /task ..."
        normalized = re.sub(r'^\s*[❯>$#]+\s*', '', line)

        # Must start with /task or TASK: (after stripping leading whitespace)
        stripped = normalized.lstrip()
        if not (stripped.startswith('/task') or stripped.startswith('TASK:')):
            return None

        # Match /task <prompt>
        match = self.PATTERN_TASK.match(normalized)
        if match:
            return match.group(1).strip()

        # Match TASK: <prompt>
        match = self.PATTERN_TASK_COLON.match(normalized)
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
        self.worker_window = os.environ.get('AI_SWARM_BRIDGE_WORKER_WINDOW', 'workers')
        self.worker_panes = os.environ.get('AI_SWARM_BRIDGE_WORKER_PANES', '')
        self.direct_fallback = os.environ.get('AI_SWARM_BRIDGE_DIRECT_FALLBACK', '1') == '1'
        self.poll_interval = float(os.environ.get(
            'AI_SWARM_BRIDGE_POLL_INTERVAL', '1.0'))
        self.capture_lines = int(os.environ.get('AI_SWARM_BRIDGE_LINES', '200'))
        self.ai_swarm_dir = os.environ.get('AI_SWARM_DIR', '/tmp/ai_swarm')
        self.fifo_path = os.path.join(self.ai_swarm_dir, 'master_inbox')

        # ACK and retry configuration
        self.ack_timeout = float(os.environ.get('AI_SWARM_BRIDGE_ACK_TIMEOUT', '10.0'))
        self.max_retries = int(os.environ.get('AI_SWARM_BRIDGE_MAX_RETRIES', '3'))
        self.retry_delay = float(os.environ.get('AI_SWARM_BRIDGE_RETRY_DELAY', '2.0'))

        # Components
        self.parser = TaskParser()
        dedupe_file = os.path.join(self.ai_swarm_dir, 'bridge_dedupe.json')
        # Cache size: max(100, capture_lines * 2) to ensure all tasks in capture window are remembered
        dedupe_cache_size = max(100, self.capture_lines * 2)
        self.dedupe = DedupeState(dedupe_file, cache_size=dedupe_cache_size)

        # Task ID generator (for dispatch tracking)
        id_file = os.path.join(self.ai_swarm_dir, 'bridge_task_ids.txt')
        self.task_id_generator = BridgeTaskIdGenerator(id_file)

        # FIFO write failure throttling
        self._last_fifo_error_time = 0.0
        self._fifo_error_cooldown = 10.0  # 10 second cooldown

        # Status broadcaster (lazy load)
        self._broadcaster = None
        self._broadcaster_init_failed = False
        self._dispatch_index = 0

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

    def _send_text_to_pane(self, pane_id: str, text: str) -> bool:
        """
        Send one line of text to a specific pane.

        Uses two calls so Enter is sent as a key (not literal text).
        """
        try:
            subprocess.run(
                ['tmux', 'send-keys', '-l', '-t', pane_id, text],
                capture_output=True,
                timeout=5
            )
            subprocess.run(
                ['tmux', 'send-keys', '-t', pane_id, 'Enter'],
                capture_output=True,
                timeout=5
            )
            return True
        except Exception:
            return False

    def _get_worker_panes(self):
        """
        Resolve worker pane IDs for direct dispatch.

        Priority:
        1) AI_SWARM_BRIDGE_WORKER_PANES (comma-separated pane ids)
        2) tmux list-panes -t <session>:<worker_window>
        """
        if self.worker_panes.strip():
            return [p.strip() for p in self.worker_panes.split(',') if p.strip()]

        pane_spec = f"{self.session}:{self.worker_window}"
        try:
            result = subprocess.run(
                ['tmux', 'list-panes', '-t', pane_spec, '-F', '#{pane_id}'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                return []
            return [line.strip() for line in result.stdout.splitlines() if line.strip()]
        except Exception:
            return []

    def _capture_worker_pane(self, pane_id: str) -> str:
        """
        Capture content from a worker pane.

        Args:
            pane_id: tmux pane ID (e.g., %4)

        Returns:
            Captured pane content as string
        """
        try:
            result = subprocess.run(
                ['tmux', 'capture-pane', '-t', pane_id, '-p'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout
        except Exception:
            return ""

    def _wait_for_ack(self, bridge_task_id: str, target_pane: str, timeout: float = None) -> Tuple[bool, float]:
        """
        Wait for ACK confirmation from worker.

        After dispatching to a worker, capture the worker pane periodically
        to check for ACK pattern: [ACK] <bridge-task-id>

        Args:
            bridge_task_id: The task ID to look for in ACK
            target_pane: The pane ID to capture (worker pane)
            timeout: Timeout in seconds (default: self.ack_timeout)

        Returns:
            (ack_received: bool, latency_ms: float)
            - ack_received: True if ACK found, False on timeout
            - latency_ms: Time from dispatch to ACK in milliseconds
        """
        if timeout is None:
            timeout = self.ack_timeout

        start_time = time.time()
        poll_interval = 0.5  # Check every 500ms

        # ACK pattern to match
        ack_pattern = re.compile(r'\[ACK\]\s*' + re.escape(bridge_task_id))

        while True:
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                # Timeout reached
                return False, elapsed * 1000

            # Capture worker pane and check for ACK
            capture = self._capture_worker_pane(target_pane)
            if ack_pattern.search(capture):
                latency_ms = (time.time() - start_time) * 1000
                return True, latency_ms

            # Sleep before next check
            time.sleep(poll_interval)

    def _dispatch_to_worker(self, task: str, bridge_task_id: str = None) -> Tuple[bool, str, float, list]:
        """
        Direct-dispatch task to worker panes with ACK verification and retry.

        Implements the dispatch protocol:
        1. Select worker (round-robin)
        2. Dispatch task with bridge_task_id
        3. Wait for ACK from worker
        4. If ACK: return success with latency
        5. If timeout: retry same worker (up to max_retries)
        6. If all retries exhausted: fail over to next worker
        7. If all workers fail: raise BridgeDispatchError

        Args:
            task: Task prompt to dispatch
            bridge_task_id: Optional bridge task ID (generated if not provided)

        Returns:
            Tuple of (success: bool, worker_pane: str, latency_ms: float, attempts: list)
            - success: True if dispatch acknowledged
            - worker_pane: The pane that acknowledged
            - latency_ms: Time from dispatch to ACK
            - attempts: List of (pane, success, latency_ms) for all attempts

        Raises:
            BridgeDispatchError: If all workers fail after all retries
        """
        # Generate bridge_task_id if not provided
        if not bridge_task_id:
            bridge_task_id = self.task_id_generator.generate()

        panes = self._get_worker_panes()
        if not panes:
            raise BridgeDispatchError(
                bridge_task_id,
                [],
                "No worker panes available"
            )

        attempts = []
        total_attempts = 0
        max_total_attempts = self.max_retries * len(panes)

        # Track which workers we've tried (for round-robin with failover)
        pane_index = self._dispatch_index % len(panes)
        self._dispatch_index += len(panes)  # Advance by full cycle for next dispatch

        # Log CAPTURED phase (task captured from master)
        self._log_phase(
            phase=BridgePhase.CAPTURED,
            bridge_task_id=bridge_task_id,
            task_preview=task[:100]
        )

        # Log PARSED phase (task ready for dispatch)
        self._log_phase(
            phase=BridgePhase.PARSED,
            bridge_task_id=bridge_task_id,
            task_preview=task[:100]
        )

        # Try each worker in round-robin, with retries per worker
        while total_attempts < max_total_attempts:
            pane_id = panes[pane_index % len(panes)]
            pane_index += 1
            total_attempts += 1

            # Calculate which retry attempt this is for current worker
            worker_attempt = ((total_attempts - 1) % self.max_retries) + 1

            # Log DISPATCHED phase
            dispatch_start = time.time()
            self._log_phase(
                phase=BridgePhase.DISPATCHED,
                bridge_task_id=bridge_task_id,
                task_preview=task[:100],
                target_worker=pane_id,
                attempt=total_attempts,
                dispatch_mode=DispatchMode.DIRECT
            )

            # Send task to worker pane
            payload = f"[BRIDGE_TASK_ID: {bridge_task_id}] TASK: {task}"
            send_success = self._send_text_to_pane(pane_id, payload)

            if not send_success:
                # Send failed, log and continue to next attempt
                latency_ms = (time.time() - dispatch_start) * 1000
                attempts.append((pane_id, False, latency_ms, "send_keys_failed"))
                continue

            # Wait for ACK from worker
            ack_received, latency_ms = self._wait_for_ack(bridge_task_id, pane_id)

            if ack_received:
                # Success! Log ACKED phase
                self._log_phase(
                    phase=BridgePhase.ACKED,
                    bridge_task_id=bridge_task_id,
                    task_preview=task[:100],
                    target_worker=pane_id,
                    attempt=total_attempts,
                    latency_ms=latency_ms,
                    dispatch_mode=DispatchMode.DIRECT
                )
                return True, pane_id, latency_ms, attempts

            else:
                # ACK timeout, log RETRY phase
                attempts.append((pane_id, False, latency_ms, "ack_timeout"))

                # Determine if we should retry same worker or failover
                if worker_attempt < self.max_retries:
                    # Retry same worker
                    self._log_phase(
                        phase=BridgePhase.RETRY,
                        bridge_task_id=bridge_task_id,
                        task_preview=task[:100],
                        target_worker=pane_id,
                        attempt=total_attempts,
                        latency_ms=latency_ms,
                        dispatch_mode=DispatchMode.DIRECT,
                        reason="ack_timeout"
                    )
                    # Don't advance pane_index (retry same worker)
                    # Add retry delay
                    time.sleep(self.retry_delay)
                else:
                    # All retries exhausted for this worker, failover to next
                    self._log_phase(
                        phase=BridgePhase.RETRY,
                        bridge_task_id=bridge_task_id,
                        task_preview=task[:100],
                        target_worker=pane_id,
                        attempt=total_attempts,
                        latency_ms=latency_ms,
                        dispatch_mode=DispatchMode.DIRECT,
                        reason="worker_failover"
                    )
                    # Small delay before trying next worker
                    time.sleep(self.retry_delay)

        # All attempts exhausted, log FAILED phase
        self._log_phase(
            phase=BridgePhase.FAILED,
            bridge_task_id=bridge_task_id,
            task_preview=task[:100],
            target_worker=panes[pane_index % len(panes)],
            attempt=total_attempts,
            dispatch_mode=DispatchMode.DIRECT,
            attempts_summary=len(attempts)
        )

        raise BridgeDispatchError(
            bridge_task_id,
            attempts,
            f"All {max_total_attempts} attempts failed"
        )

    def _write_to_fifo(self, task: str) -> bool:
        """
        Write to FIFO and send dispatch confirmation via send-keys.

        Uses structured logging for dispatch tracking with bridge_task_id.

        Args:
            task: Task prompt to write

        Returns:
            True on success, False if no reader
        """
        # Generate bridge_task_id for this dispatch
        bridge_task_id = self.task_id_generator.generate()

        # Log CAPTURED phase
        self._log_phase(
            phase=BridgePhase.CAPTURED,
            bridge_task_id=bridge_task_id,
            task_preview=task[:100]
        )

        # Log PARSED phase
        self._log_phase(
            phase=BridgePhase.PARSED,
            bridge_task_id=bridge_task_id,
            task_preview=task[:100]
        )

        success = write_to_fifo_nonblocking(self.fifo_path, task)

        now = time.time()
        if success:
            # FIFO write succeeded - dispatch via FIFO
            # Send dispatch confirmation to master window via send-keys
            dispatch_msg = f"[DISPATCHED] {task[:60]}"
            self._send_keys(dispatch_msg)

            sys.stdout.write(f"[Bridge] -> FIFO: {task[:60]}...\n")
            sys.stdout.flush()

            # Log DISPATCHED phase with FIFO mode
            self._log_phase(
                phase=BridgePhase.DISPATCHED,
                bridge_task_id=bridge_task_id,
                task_preview=task[:100],
                target_worker="master",
                dispatch_mode=DispatchMode.FIFO
            )

            # Log ACKED phase immediately for FIFO mode (master acknowledges receipt)
            self._log_phase(
                phase=BridgePhase.ACKED,
                bridge_task_id=bridge_task_id,
                task_preview=task[:100],
                target_worker="master",
                dispatch_mode=DispatchMode.FIFO,
                latency_ms=0
            )

            return True
        else:
            # FIFO failed - use direct dispatch to workers
            if self.direct_fallback:
                try:
                    success, pane_id, latency_ms, attempts = self._dispatch_to_worker(
                        task, bridge_task_id
                    )
                    if success:
                        dispatch_msg = f"[DISPATCHED->WORKER {pane_id}] {task[:60]}"
                        self._send_keys(dispatch_msg)
                        sys.stdout.write(
                            f"[Bridge] -> worker({pane_id}): {task[:60]}...\n"
                        )
                        sys.stdout.flush()
                        return True
                except BridgeDispatchError as e:
                    sys.stderr.write(f"[Bridge] Dispatch failed: {e}\n")
                    return False

            # Throttling: avoid repeated spam
            if now - self._last_fifo_error_time >= self._fifo_error_cooldown:
                sys.stderr.write(
                    "[Bridge] FIFO write failed (no reader), and direct dispatch unavailable\n"
                )
                self._last_fifo_error_time = now

                # Log FAILED phase
                self._log_phase(
                    phase=BridgePhase.FAILED,
                    bridge_task_id=bridge_task_id,
                    task_preview=task[:100],
                    dispatch_mode=DispatchMode.FIFO,
                    reason="fifo_no_reader"
                )

        return success

    def _log_phase(
        self,
        phase: str,
        bridge_task_id: str = None,
        task_preview: str = None,
        target_worker: str = None,
        attempt: int = 1,
        latency_ms: float = None,
        **extra
    ):
        """
        Write structured phase log to bridge.log.

        Changes bridge.log format from:
            [2026-02-06 10:00:00] dispatched
        To:
            {"ts":"2026-02-06T10:00:00.000Z","phase":"DISPATCHED","bridge_task_id":"br-1234567890-abc","task":"Fix bug","target_worker":"%4","attempt":1}

        Args:
            phase: BridgePhase value (CAPTURED, PARSED, DISPATCHED, etc.)
            bridge_task_id: Unique ID from BridgeTaskIdGenerator
            task_preview: First 100 chars of task prompt
            target_worker: Target pane ID (e.g., %4)
            attempt: Dispatch attempt number (1-indexed)
            latency_ms: Time from dispatch to this phase in milliseconds
            **extra: Additional fields to include in log
        """
        from datetime import datetime, timezone

        # ISO 8601 timestamp with millisecond precision
        ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

        # Build structured log entry
        entry = {
            "ts": ts,
            "phase": phase,
        }

        # Add optional fields
        if bridge_task_id:
            entry["bridge_task_id"] = bridge_task_id
        if task_preview:
            entry["task_preview"] = task_preview[:100] if task_preview else None
        if target_worker:
            entry["target_worker"] = target_worker
        if attempt is not None:
            entry["attempt"] = attempt
        if latency_ms is not None:
            entry["latency_ms"] = round(latency_ms, 2)

        # Add any extra fields
        for k, v in extra.items():
            entry[k] = v

        # Write to bridge.log as JSON (one JSON object per line)
        try:
            os.makedirs(self.ai_swarm_dir, exist_ok=True)
            log_file = os.path.join(self.ai_swarm_dir, 'bridge.log')
            with open(log_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except (IOError, OSError):
            pass

        # Also write to status.log via broadcaster for compatibility
        bc = self._get_broadcaster()
        if bc:
            from swarm.status_broadcaster import BroadcastState
            try:
                bc.broadcast(
                    state=BroadcastState.HELP,
                    task_id=bridge_task_id or "",
                    message=phase,
                    meta={
                        "type": "BRIDGE",
                        "bridge_phase": phase,
                        "bridge_task_id": bridge_task_id,
                        "target_worker": target_worker,
                        "attempt": attempt,
                        **extra
                    }
                )
            except Exception:
                pass

    def _log_status(self, status: str, **extra):
        """
        Legacy status logging method - delegates to _log_phase.

        DEPRECATED: Use _log_phase() for new code.
        This method is kept for backward compatibility with existing calls.

        Args:
            status: Status message (maps to bridge_phase for structured logging)
            **extra: Additional fields
        """
        # Map legacy status to phase
        status_to_phase = {
            "started": BridgePhase.CAPTURED,
            "task_sent": BridgePhase.DISPATCHED,
            "dispatched": BridgePhase.DISPATCHED,
            "dispatched_direct": BridgePhase.DISPATCHED,
            "skipped_duplicate": BridgePhase.PARSED,
            "fifo_no_reader": BridgePhase.FAILED,
            "stopped": BridgePhase.FAILED,
            "error": BridgePhase.FAILED,
        }
        phase = status_to_phase.get(status, status.upper())

        # Call _log_phase with appropriate fields
        self._log_phase(
            phase=phase,
            task_preview=extra.get('task', extra.get('task_hash', ''))[:100] if extra else None,
            **extra
        )  # Broadcaster may be unavailable

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
