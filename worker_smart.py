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
from datetime import datetime
from pathlib import Path

import config
import task_queue


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

        # Set base directory
        if base_dir is None:
            self.base_dir = os.path.expanduser('~/group/ai_swarm/')
        else:
            self.base_dir = base_dir

        # Setup paths
        self.status_log = os.path.join(self.base_dir, 'status.log')
        self.locks_dir = os.path.join(self.base_dir, 'locks')
        self.results_dir = os.path.join(self.base_dir, 'results')
        self.instructions_dir = os.path.join(self.base_dir, 'instructions')
        self.lock_file = os.path.join(self.locks_dir, f'{self.name}.lock')

        # Ensure directories exist
        os.makedirs(self.locks_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)
        os.makedirs(self.instructions_dir, exist_ok=True)

        # Register signal handlers
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

        # Load API key
        try:
            self.api_key = config.get_api_key()
        except RuntimeError as e:
            print(f"[{self.name}] Configuration error: {e}")
            raise

    def shutdown(self, signum, frame):
        """
        Handle shutdown signals gracefully

        Args:
            signum: Signal number received
            frame: Current stack frame
        """
        print(f"\n[{self.name}] Received signal {signum}, shutting down...")
        self.write_status('SHUTDOWN', f'Received signal {signum}')
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

    def write_status(self, status, msg):
        """
        Write status update to log

        Args:
            status: Status code
            msg: Status message
        """
        try:
            log_entry = {
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'node': self.name,
                'status': status,
                'msg': msg
            }

            with open(self.status_log, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
                f.flush()

            print(f"[{self.name}] [{status}] {msg}")

        except Exception as e:
            print(f"[{self.name}] Error writing status: {e}")

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
            self.write_status('ERROR', error_msg)
            raise Exception(error_msg)

        except requests.exceptions.ConnectionError:
            error_msg = 'Network connection failed'
            self.write_status('ERROR', error_msg)
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

            self.write_status('ERROR', error_msg)
            raise Exception(error_msg)

        except Exception as e:
            # Catch-all for other errors
            error_msg = f'Unexpected error: {e}'
            self.write_status('ERROR', error_msg)
            raise Exception(error_msg)

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
        Process task with streaming responses and jittered status updates

        Args:
            task: Task dictionary with all parameters

        Returns:
            str: Path to result file
        """
        task_id = task['id']
        prompt = task['prompt']
        system = task.get('system')
        max_tokens = task.get('max_tokens', config.DEFAULT_MAX_TOKENS)
        model = task.get('model', config.DEFAULT_MODEL)

        # START
        self.write_status('START', f'Starting task: {task_id}')

        try:
            # Call API (simplified - in real implementation would use streaming)
            response = self.call_claude_api(prompt, system, max_tokens, model)

            # Extract content and usage
            content = response['content'][0]['text']
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
                    self.write_status('THINKING', f'Generating... (~{token_count} tokens)')

                    # 🆕 Jitter: sleep for 2-3 seconds
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

            # Calculate and log cost
            model = task.get('model', config.DEFAULT_MODEL)
            cost = config.calculate_cost(model, input_tokens, output_tokens)

            self.write_status(
                'DONE',
                f'Completed: {task_id} | Tokens: {input_tokens}+{output_tokens} | Cost: ${cost:.6f}'
            )

            return result_file

        except Exception as e:
            self.write_status('ERROR', f'Task {task_id} failed: {e}')
            raise

    def poll_for_instructions(self):
        """
        Poll for instruction files from dispatcher

        Returns:
            dict: Task parameters or None
        """
        instruction_file = os.path.join(self.instructions_dir, f'{self.name}.json')

        if os.path.exists(instruction_file):
            try:
                with open(instruction_file, 'r') as f:
                    task = json.load(f)

                # Consume the instruction file
                os.remove(instruction_file)

                print(f"[{self.name}] Received task: {task.get('task_id')}")
                return task

            except Exception as e:
                print(f"[{self.name}] Error reading instruction file: {e}")
                return None

        return None

    def run(self):
        """
        Main worker loop

        Returns:
            int: Exit code
        """
        if not self.acquire_lock():
            return 1

        # Write initial status so dispatcher can detect this worker
        self.write_status('START', 'Smart Worker initialized')

        print(f"[{self.name}] Smart Worker started")
        print(f"[{self.name}] Model: {config.DEFAULT_MODEL}")

        try:
            while self.running:
                # Poll for instructions
                task = self.poll_for_instructions()

                if task:
                    try:
                        self.process_task_streaming(task)
                    except Exception as e:
                        print(f"[{self.name}] Task processing error: {e}")
                else:
                    # No task, wait before next poll
                    time.sleep(2)

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
