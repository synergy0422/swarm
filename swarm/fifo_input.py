#!/usr/bin/env python3
"""
FIFO Input Channel for AI Swarm System

Provides a named pipe (FIFO) input channel for master to accept natural language tasks.
Non-blocking read using os.open() with O_NONBLOCK + select.poll().

Usage:
  - Set AI_SWARM_INTERACTIVE=1 to enable
  - Master creates FIFO at $AI_SWARM_DIR/master_inbox
  - Write tasks to FIFO using swarm task add or swarm_fifo_write.sh
"""

import os
import stat
import sys
import select
import errno
import time
import fcntl
from typing import Optional


def get_fifo_path() -> str:
    """
    Get FIFO path, respects AI_SWARM_DIR env var (NOT AI_SWARM_TASKS_FILE).

    Returns:
        str: Path to master_inbox FIFO
    """
    base_dir = os.environ.get('AI_SWARM_DIR', '/tmp/ai_swarm')
    return os.path.join(base_dir, 'master_inbox')


def get_interactive_mode() -> bool:
    """
    Check if interactive mode is enabled.

    Returns:
        bool: True if AI_SWARM_INTERACTIVE=1
    """
    return os.environ.get('AI_SWARM_INTERACTIVE', '0') == '1'


def write_to_fifo_nonblocking(fifo_path: str, text: str) -> bool:
    """
    Write to FIFO with O_NONBLOCK.

    Args:
        fifo_path: Path to the FIFO
        text: Text to write

    Returns:
        True on success, False if no reader (EAGAIN/EWOULDBLOCK)
    Raises:
        Exception: On other errors (FileNotFoundError, etc.)
    """
    fd = os.open(fifo_path, os.O_WRONLY | os.O_NONBLOCK)
    try:
        os.write(fd, (text + '\n').encode('utf-8'))
        return True
    except OSError as e:
        if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
            return False  # No reader
        raise
    finally:
        os.close(fd)


class FifoInputHandler:
    """
    Handles FIFO input for natural language task entry.

    Creates its own TaskQueue instance internally (respects AI_SWARM_TASKS_FILE).
    Non-blocking read using os.open() O_NONBLOCK + select.poll().
    """

    def __init__(self):
        """Initialize FIFO input handler."""
        self.running = True
        self.fifo_path = get_fifo_path()
        # FifoInputHandler creates its own TaskQueue (respects AI_SWARM_TASKS_FILE)
        from swarm.task_queue import TaskQueue
        self._task_queue = TaskQueue()
        self._broadcaster = None  # Set by Master if provided

    def _ensure_fifo_exists(self):
        """Create FIFO if not exists."""
        if not os.path.exists(self.fifo_path):
            os.mkfifo(self.fifo_path, mode=0o666)

    def _read_line_nonblocking(self) -> str:
        """
        Read from FIFO using O_NONBLOCK + select.poll().

        Returns:
            str: Line content, or empty string on timeout, EOF, or POLLHUP.
            Does NOT block indefinitely.
        """
        fd = None
        try:
            fd = os.open(self.fifo_path, os.O_RDONLY | os.O_NONBLOCK)
            # Clear O_NONBLOCK for poll (we want to know when data arrives)
            flags = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, flags & ~os.O_NONBLOCK)

            poll_obj = select.poll()
            poll_obj.register(fd, select.POLLIN)

            events = poll_obj.poll(1000)  # 1 second timeout

            if not events:
                return ''  # Timeout, no data

            # Check for POLLHUP (hangup) - reader closed
            for event in events:
                if event & (select.POLLHUP | select.POLLERR):
                    return ''  # Reader closed

            # Data available, read it
            try:
                data = os.read(fd, 4096)
                if not data:
                    return ''  # EOF
                return data.decode('utf-8').rstrip('\n')
            except OSError as e:
                if e.errno == errno.EAGAIN:
                    return ''  # No data available
                raise
        except FileNotFoundError:
            return ''  # FIFO doesn't exist yet
        except (OSError, IOError) as e:
            if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                return ''
            return ''
        finally:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass

    def _parse_command(self, line: str) -> tuple:
        """
        Parse line and return (command, payload).

        Returns:
            tuple: (command, payload) where:
            - ('task', prompt) for /task <prompt> or plain text
            - ('help', None) for /help
            - ('quit', None) for /quit
            - ('ignore', None) for empty/whitespace
            - ('error', msg) for /task without prompt
        """
        line = line.strip()
        if not line:
            return ('ignore', None)

        if line.startswith('/'):
            parts = line.split(None, 1)
            cmd = parts[0].lower()
            if cmd == '/task':
                if len(parts) < 2 or not parts[1].strip():
                    return ('error', '/task requires a prompt')
                return ('task', parts[1])
            elif cmd == '/help':
                return ('help', None)
            elif cmd == '/quit':
                return ('quit', None)
            else:
                return ('error', f'Unknown command: {cmd}')

        # Plain text treated as task prompt
        return ('task', line)

    def _handle_task(self, prompt: str):
        """Call task_queue.add_task(prompt), log result."""
        if not prompt:
            return
        try:
            task_id = self._task_queue.add_task(prompt)
            # broadcast_start() signature: (task_id, message, meta=None)
            # Note: No worker_id parameter
            if self._broadcaster:
                self._broadcaster.broadcast_start(task_id=task_id, message=f"FIFO: {prompt[:50]}")
            sys.stdout.write(f"[FIFO] Created task: {task_id}\n")
            sys.stdout.flush()
        except Exception as e:
            sys.stderr.write(f"[FIFO] Failed to create task: {e}\n")
            sys.stderr.flush()

    def _handle_help(self):
        """Print help text."""
        sys.stdout.write("""
=== FIFO Input Commands ===

/task <prompt>   Create a new task with the given prompt
/help            Show this help message
/quit            Stop the FIFO input thread (master continues)

Examples:
  /task Review PR #123 and leave comments
  /task Fix authentication bug in login module

Plain text (without /task prefix) is also treated as a task prompt.

Note: Use 'swarm task add "<prompt>"' from CLI or 'echo "<prompt>" | ./scripts/swarm_fifo_write.sh write -' to write to FIFO.
""")
        sys.stdout.flush()

    def run(self):
        """Main loop - read, parse, handle."""
        self._ensure_fifo_exists()
        sys.stdout.write(f"[FIFO] Input thread started, listening on {self.fifo_path}\n")
        sys.stdout.flush()

        while self.running:
            try:
                line = self._read_line_nonblocking()
                if line is None:
                    continue

                cmd, payload = self._parse_command(line)

                if cmd == 'ignore':
                    continue
                elif cmd == 'task':
                    self._handle_task(payload)
                elif cmd == 'help':
                    self._handle_help()
                elif cmd == 'quit':
                    sys.stdout.write("[FIFO] Input thread stopping...\n")
                    sys.stdout.flush()
                    self.running = False
                elif cmd == 'error':
                    sys.stderr.write(f"[FIFO] Error: {payload}\n")
                    sys.stderr.flush()

            except Exception as e:
                sys.stderr.write(f"[FIFO] Error: {e}\n")
                sys.stderr.flush()

        sys.stdout.write("[FIFO] Input thread stopped\n")
        sys.stdout.flush()

    def _shutdown(self):
        """Signal handler calls this to stop the input thread."""
        self.running = False
