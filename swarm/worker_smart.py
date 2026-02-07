#!/usr/bin/env python3
"""
Smart Worker Node with Anthropic API Integration

Processes tasks using Claude API with streaming support and cost tracking.
"""

import os
import sys
import json
import time
import random
import signal
import fcntl
import shutil
import requests
import threading
from datetime import datetime, timezone
from pathlib import Path

from swarm import config
from swarm import task_queue
from swarm.status_broadcaster import StatusBroadcaster, BroadcastState
from swarm.task_lock import TaskLockManager


class SmartWorker:
    """Smart worker that calls Anthropic Claude API"""

    def __init__(self, name, base_dir=None):
        """
        Initialize smart worker

        Args:
            name: Worker identifier (e.g., 'worker-1')
            base_dir: Base directory for swarm files
        """
        self.name = name
        self.running = True
        self.lock_fd = None
        self._mailbox_offset = 0  # Track read position in mailbox

        # Set base directory
        if base_dir is None:
            self.base_dir = os.environ.get('AI_SWARM_DIR', '/tmp/ai_swarm/')
        else:
            self.base_dir = base_dir

        # Auto-create base directory
        os.makedirs(self.base_dir, exist_ok=True)

        # Setup paths
        self.status_log = os.path.join(self.base_dir, 'status.log')
        self.locks_dir = os.path.join(self.base_dir, 'locks')
        self.results_dir = os.path.join(self.base_dir, 'results')
        self.instructions_dir = os.path.join(self.base_dir, 'instructions')
        self.offsets_dir = os.path.join(self.base_dir, 'offsets')
        self.lock_file = os.path.join(self.locks_dir, f'{self.name}.lock')
        self.mailbox_path = os.path.join(self.instructions_dir, f'{self.name}.jsonl')
        self._offset_file_path = os.path.join(self.offsets_dir, f'{self.name}.offset.json')

        # Ensure directories exist
        os.makedirs(self.locks_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)
        os.makedirs(self.instructions_dir, exist_ok=True)
        os.makedirs(self.offsets_dir, exist_ok=True)

        # Initialize status broadcaster for unified JSONL logging
        self.broadcaster = StatusBroadcaster(worker_id=self.name)

        # Initialize task lock manager for task-level locking
        self.lock_manager = TaskLockManager(worker_id=self.name)

        # Register signal handlers
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

        # Load API key
        try:
            self.api_key = config.get_api_key()
        except RuntimeError as e:
            print(f"[{self.name}] Configuration error: {e}")
            raise

        # Load persisted mailbox offset (P1.1: prevent duplicate consumption on restart)
        self._mailbox_offset = self._load_mailbox_offset()

    def _load_mailbox_offset(self) -> int:
        """
        Load persisted mailbox offset from file.

        Returns:
            int: Last saved offset, or 0 if file doesn't exist or is corrupted
        """
        if not os.path.exists(self._offset_file_path):
            return 0

        try:
            with open(self._offset_file_path, 'r') as f:
                data = json.load(f)
            return int(data.get('offset', 0))
        except (json.JSONDecodeError, ValueError, OSError):
            print(f"[{self.name}] Failed to load offset file, starting from 0")
            return 0

    def _save_mailbox_offset(self, offset: int) -> None:
        """
        Persist mailbox offset to file atomically.

        Args:
            offset: The offset value to save
        """
        temp_path = self._offset_file_path + '.tmp.' + str(os.getpid())
        try:
            data = {
                'offset': offset,
                'updated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            }
            with open(temp_path, 'w') as f:
                json.dump(data, f)
            os.replace(temp_path, self._offset_file_path)
        except (OSError, IOError) as e:
            print(f"[{self.name}] Failed to save offset: {e}")
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def shutdown(self, signum, frame):
        """
        Handle shutdown signals gracefully

        Args:
            signum: Signal number received
            frame: Current stack frame
        """
        print(f"\n[{self.name}] Received signal {signum}, shutting down...")
        self.broadcaster.broadcast_done(task_id="", message=f'Received signal {signum}')
        self.release_lock()
        self.running = False

    def acquire_lock(self):
        """
        Acquire exclusive lock file

        Returns:
            bool: True if lock acquired
        """
        try:
            self.lock_fd = open(self.lock_file, 'w')
            fcntl.flock(
                self.lock_fd.fileno(),
                fcntl.LOCK_EX | fcntl.LOCK_NB
            )

            self.lock_fd.write(str(os.getpid()))
            self.lock_fd.flush()

            print(f"[{self.name}] Lock acquired")
            return True

        except IOError:
            print(f"[{self.name}] Failed to acquire lock (already running?)")
            return False

    def release_lock(self):
        """Release lock file"""
        if self.lock_fd:
            try:
                fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_UN)
                self.lock_fd.close()

                if os.path.exists(self.lock_file):
                    os.remove(self.lock_file)

            except Exception as e:
                print(f"[{self.name}] Error releasing lock: {e}")

    @staticmethod
    def calculate_jitter():
        """
        Calculate random jitter for status updates

        Returns:
            float: Jitter value in seconds (0-1)
        """
        return random.uniform(*config.JITTER_RANGE)

    def call_claude_api(self, prompt, system=None, max_tokens=None, model=None):
        """
        Call Anthropic Claude API

        Args:
            prompt: User prompt
            system: Optional system prompt
            max_tokens: Optional max tokens override
            model: Optional model override

        Returns:
            dict: API response

        Raises:
            Exception: On API errors
        """
        # Use defaults if not provided
        if max_tokens is None:
            max_tokens = config.DEFAULT_MAX_TOKENS
        if model is None:
            model = config.DEFAULT_MODEL

        # Build request
        headers = {
            'anthropic-version': config.ANTHROPIC_API_VERSION,
            'content-type': 'application/json'
        }

        # Only add API key if not using proxy mode
        if self.api_key:  # Will be empty string in proxy mode
            headers['x-api-key'] = self.api_key

        body = {
            'model': model,
            'max_tokens': max_tokens,
            'messages': [{'role': 'user', 'content': prompt}]
        }

        # Add system prompt if provided
        if system:
            body['system'] = system

        try:
            # Use correct endpoint (supports ccswitch proxy)
            api_endpoint = config.get_api_endpoint()
            response = requests.post(
                api_endpoint,
                headers=headers,
                json=body,
                timeout=config.REQUEST_TIMEOUT
            )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            error_msg = 'API request timed out'
            self.broadcaster.broadcast_error(task_id="", message=error_msg)
            raise Exception(error_msg)

        except requests.exceptions.ConnectionError:
            error_msg = 'Network connection failed'
            self.broadcaster.broadcast_error(task_id="", message=error_msg)
            raise Exception(error_msg)

        except requests.exceptions.HTTPError as e:
            status_code = getattr(e.response, 'status_code', None)

            if status_code == 401:
                error_msg = 'Invalid API key'
            elif status_code == 429:
                error_msg = 'Rate limit exceeded'
            elif status_code == 500:
                error_msg = 'Anthropic API error (500)'
            else:
                error_msg = f'API error ({status_code})'

            self.broadcaster.broadcast_error(task_id="", message=error_msg)
            raise Exception(error_msg)

        except Exception as e:
            # Catch-all for other errors
            error_msg = f'Unexpected error: {e}'
            self.broadcaster.broadcast_error(task_id="", message=error_msg)
            raise Exception(error_msg)

    def _extract_response_text(self, response):
        """
        Extract text content from various response schemas.

        Supports Anthropic-style content blocks and proxy variants.
        """
        content = response.get('content')
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    if 'text' in item:
                        return item['text']
                    if 'content' in item:
                        return item['content']
                    if 'thinking' in item:
                        return item['thinking']
        if isinstance(content, str):
            return content

        # Fallback: OpenAI-like schema
        choices = response.get('choices')
        if isinstance(choices, list) and choices:
            msg = choices[0].get('message', {})
            if isinstance(msg, dict) and 'content' in msg:
                return msg['content']

        raise KeyError("No text content found in response")

    def save_result(self, task_id, content, task_params, input_tokens, output_tokens):
        """
        Save result to markdown file with metadata

        Args:
            task_id: Task identifier
            content: AI response content
            task_params: Task parameters dictionary
            input_tokens: Input tokens used
            output_tokens: Output tokens used
        """
        result_file = os.path.join(self.results_dir, f'{task_id}.md')

        # Calculate cost
        model = task_params.get('model', config.DEFAULT_MODEL)
        cost = config.calculate_cost(model, input_tokens, output_tokens)

        # Build metadata header
        metadata = {
            'task_id': task_id,
            'worker': self.name,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'model': model,
            'max_tokens': task_params.get('max_tokens', config.DEFAULT_MAX_TOKENS),
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_cost': f"${cost:.6f}"
        }

        # Add optional fields
        if 'system' in task_params:
            metadata['system'] = task_params['system']

        # Write to file
        with open(result_file, 'w') as f:
            f.write('---\n')
            for key, value in metadata.items():
                f.write(f'{key}: {value}\n')
            f.write('---\n\n')
            f.write(content)

        print(f"[{self.name}] Result saved to: {result_file}")

        return result_file

    def process_task_streaming(self, task):
        """
        Process task with streaming responses and jittered status updates.

        Uses task-level locking to prevent duplicate execution across workers.
        Heartbeat is updated every 10 seconds while holding the lock.

        Args:
            task: Task dictionary with all parameters

        Returns:
            str: Path to result file, or None if lock acquisition failed
        """
        task_id = task['id']
        prompt = task['prompt']
        system = task.get('system')
        max_tokens = task.get('max_tokens', config.DEFAULT_MAX_TOKENS)
        model = task.get('model', config.DEFAULT_MODEL)

        # Try to acquire task lock
        if not self.lock_manager.acquire_lock(task_id):
            # Task is already being processed by another worker
            self.broadcaster.broadcast_skip(
                task_id=task_id,
                message=f'Task {task_id} already locked, skipping'
            )
            return None

        # Background heartbeat thread
        heartbeat_stop = threading.Event()
        heartbeat_thread = None

        def heartbeat_loop():
            """Background thread to update heartbeat every 10 seconds"""
            while not heartbeat_stop.is_set():
                self.lock_manager.update_heartbeat(task_id)
                # Wait for 10 seconds or until stop signal
                heartbeat_stop.wait(10.0)

        try:
            # START
            self.broadcaster.broadcast_start(task_id=task_id, message=f'Starting task: {task_id}')

            # Start heartbeat thread
            heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
            heartbeat_thread.start()

            # Call API (simplified - in real implementation would use streaming)
            response = self.call_claude_api(prompt, system, max_tokens, model)

            # Extract content and usage
            content = self._extract_response_text(response)
            usage = response['usage']
            input_tokens = usage['input_tokens']
            output_tokens = usage['output_tokens']

            # Simulate streaming with jittered updates
            token_count = 0
            chunk_size = max(1, output_tokens // 10)  # Simulate 10 chunks

            for i in range(10):
                token_count += chunk_size

                # Write status with jittered timing
                if i < 9:  # Don't sleep on last iteration
                    self.broadcaster.broadcast_wait(
                        task_id=task_id,
                        message=f'Generating... (~{token_count} tokens)'
                    )

                    # Jitter: sleep for 2-3 seconds
                    jitter = self.calculate_jitter()
                    time.sleep(2 + jitter)

            # DONE
            result_file = self.save_result(
                task_id,
                content,
                task,
                input_tokens,
                output_tokens
            )

            # Update tasks.json to DONE
            try:
                tq = task_queue.TaskQueue()
                tq.mark_done(task_id, result_file)
            except Exception as e:
                print(f"[{self.name}] Failed to update tasks.json to DONE: {e}")

            # Calculate and log cost
            model = task.get('model', config.DEFAULT_MODEL)
            cost = config.calculate_cost(model, input_tokens, output_tokens)

            self.broadcaster.broadcast_done(
                task_id=task_id,
                message=f'Completed: {task_id} | Tokens: {input_tokens}+{output_tokens} | Cost: ${cost:.6f}'
            )

            return result_file

        except Exception as e:
            self.broadcaster.broadcast_error(task_id=task_id, message=f'Task {task_id} failed: {e}')
            raise
        finally:
            # Stop heartbeat thread
            if heartbeat_stop:
                heartbeat_stop.set()
            # Wait for heartbeat thread to finish (with timeout)
            if heartbeat_thread and heartbeat_thread.is_alive():
                heartbeat_thread.join(timeout=1.0)

            # Always release the lock
            self.lock_manager.release_lock(task_id)

    def poll_for_instructions(self):
        """
        Poll mailbox for new RUN_TASK instructions (JSONL format).

        Reads new lines from mailbox since last read, tracking offset.
        Only processes action == "RUN_TASK" instructions.

        Returns:
            dict: Task parameters or None
        """
        if not os.path.exists(self.mailbox_path):
            return None

        try:
            with open(self.mailbox_path, 'r') as f:
                lines = f.readlines()

            # Process new lines since last offset
            for i in range(self._mailbox_offset, len(lines)):
                line = lines[i].strip()
                if not line:
                    continue

                try:
                    instruction = json.loads(line)

                    # Update offset (we've read up to this line)
                    self._mailbox_offset = i + 1
                    # P1.1: Persist offset to prevent duplicate consumption on restart
                    self._save_mailbox_offset(self._mailbox_offset)

                    # Only process RUN_TASK actions
                    if instruction.get('action') == 'RUN_TASK':
                        task_id = instruction.get('task_id')
                        payload = instruction.get('payload', {})

                        # Verify lock ownership before execution
                        if self._verify_task_lock(task_id):
                            print(f"[{self.name}] Received task: {task_id}")
                            # Convert payload to task format
                            return {
                                'id': task_id,
                                'prompt': payload.get('prompt', ''),
                                'priority': payload.get('priority', 999)
                            }
                        else:
                            # Lock not owned, skip this task
                            self.broadcaster.broadcast_skip(
                                task_id=task_id,
                                message=f'Task {task_id} lock not owned, skipping'
                            )

                except json.JSONDecodeError:
                    continue

        except Exception as e:
            print(f"[{self.name}] Error reading mailbox: {e}")

        return None

    def _verify_task_lock(self, task_id: str) -> bool:
        """
        Verify that this worker owns the lock for the task.

        Args:
            task_id: Task ID to verify

        Returns:
            bool: True if lock is owned by this worker
        """
        lock_info = self.lock_manager.get_lock_info(task_id)
        if lock_info is None:
            return False

        # Check if lock is owned by this worker
        return lock_info.worker_id == self.name

    def run(self):
        """
        Main worker loop

        Returns:
            int: Exit code
        """
        if not self.acquire_lock():
            return 1

        # Write initial status so dispatcher can detect this worker
        self.broadcaster.broadcast_start(task_id="", message='Smart Worker initialized')

        print(f"[{self.name}] Smart Worker started")
        print(f"[{self.name}] Model: {config.DEFAULT_MODEL}")

        try:
            while self.running:
                # Poll for instructions from mailbox (every 1s)
                task = self.poll_for_instructions()

                if task:
                    try:
                        self.process_task_streaming(task)
                    except Exception as e:
                        print(f"[{self.name}] Task processing error: {e}")
                else:
                    # No task, wait before next poll (1s)
                    time.sleep(1)

        except KeyboardInterrupt:
            print(f"\n[{self.name}] Interrupted by user")
        finally:
            self.release_lock()

        print(f"[{self.name}] Worker stopped")
        return 0


def calculate_cost(model, input_tokens, output_tokens):
    """
    Calculate API cost (wrapper for config.calculate_cost)

    Args:
        model: Model name
        input_tokens: Input tokens
        output_tokens: Output tokens

    Returns:
        float: Cost in USD
    """
    return config.calculate_cost(model, input_tokens, output_tokens)


def calculate_jitter():
    """
    Calculate random jitter (wrapper for compatibility)

    Returns:
        float: Jitter value (0-1)
    """
    return SmartWorker.calculate_jitter()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='AI Swarm Smart Worker'
    )
    parser.add_argument(
        '--name',
        required=True,
        help='Worker name (e.g., worker-1)'
    )
    parser.add_argument(
        '--base-dir',
        help='Base directory path (default: ~/ai_swarm/)',
        default=None
    )

    args = parser.parse_args()

    worker = SmartWorker(
        name=args.name,
        base_dir=args.base_dir
    )

    return worker.run()


if __name__ == '__main__':
    sys.exit(main())
