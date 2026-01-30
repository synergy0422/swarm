#!/usr/bin/env python3
"""
Task Queue Manager for AI Swarm System

Manages task queue persistence, assignment, and state tracking.
"""

import json
import os
import fcntl
import shutil
import time
from datetime import datetime
from pathlib import Path

from swarm import config


class TaskQueue:
    """Manages task queue with file-based persistence"""

    def __init__(self, tasks_file=None):
        """
        Initialize task queue

        Args:
            tasks_file: Path to tasks.json file
        """
        if tasks_file is None:
            base_dir = os.path.expanduser('~/group/ai_swarm/')
            tasks_file = os.path.join(base_dir, 'tasks.json')

        self.tasks_file = tasks_file
        self.backup_file = tasks_file + '.bak'

    def _acquire_lock(self, file_obj):
        """
        Acquire exclusive lock on file

        Args:
            file_obj: File object to lock

        Raises:
            IOError: If lock cannot be acquired
        """
        fcntl.flock(file_obj.fileno(), fcntl.LOCK_EX)

    def _release_lock(self, file_obj):
        """
        Release lock on file

        Args:
            file_obj: File object to unlock
        """
        fcntl.flock(file_obj.fileno(), fcntl.LOCK_UN)

    def _backup_tasks(self):
        """Create backup of tasks.json"""
        if os.path.exists(self.tasks_file):
            shutil.copy2(self.tasks_file, self.backup_file)

    def load_tasks(self):
        """
        Load tasks from file

        Returns:
            list: List of task dictionaries
        """
        if not os.path.exists(self.tasks_file):
            return []

        try:
            with open(self.tasks_file, 'r') as f:
                data = json.load(f)
                return data.get('tasks', [])
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save_tasks(self, tasks):
        """
        Save tasks to file with locking

        Args:
            tasks: List of task dictionaries
        """
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.tasks_file), exist_ok=True)

        # Write to temporary file first
        temp_file = self.tasks_file + '.tmp'

        with open(temp_file, 'w') as f:
            self._acquire_lock(f)
            try:
                json.dump({'tasks': tasks}, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            finally:
                self._release_lock(f)

        # Atomic replace
        if os.path.exists(self.tasks_file):
            os.replace(self.tasks_file, self.tasks_file + '.bak')
        os.rename(temp_file, self.tasks_file)

    def init_queue(self):
        """Create new empty queue file"""
        if not os.path.exists(self.tasks_file):
            self._save_tasks([])

    def get_pending_tasks(self):
        """
        Get all pending tasks, sorted by priority

        Returns:
            list: Pending tasks sorted by priority (1=highest)
        """
        tasks = self.load_tasks()
        pending = [t for t in tasks if t['status'] == 'pending']

        # Sort by priority (lower number = higher priority)
        return sorted(pending, key=lambda x: x.get('priority', 999))

    def assign_task(self, task_id, worker_name):
        """
        Assign task to worker

        Args:
            task_id: Task ID to assign
            worker_name: Worker to assign to
        """
        tasks = self.load_tasks()

        for task in tasks:
            if task['id'] == task_id:
                task['status'] = 'assigned'
                task['assigned_to'] = worker_name
                task['assigned_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                break

        self._save_tasks(tasks)

    def complete_task(self, task_id, result_file):
        """
        Mark task as completed

        Args:
            task_id: Task ID to complete
            result_file: Path to result file
        """
        tasks = self.load_tasks()

        for task in tasks:
            if task['id'] == task_id:
                task['status'] = 'completed'
                task['result_file'] = result_file
                task['completed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                break

        self._save_tasks(tasks)

    def fail_task(self, task_id, error_message):
        """
        Mark task as failed

        Args:
            task_id: Task ID to fail
            error_message: Error description
        """
        tasks = self.load_tasks()

        for task in tasks:
            if task['id'] == task_id:
                task['status'] = 'failed'
                task['error'] = error_message
                task['failed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                break

        self._save_tasks(tasks)

    def add_task(self, prompt, system=None, max_tokens=None, model=None, priority=5):
        """
        Add new task to queue

        Args:
            prompt: Task prompt
            system: Optional system prompt
            max_tokens: Optional max tokens override
            model: Optional model override
            priority: Task priority (1-5, default 5)

        Returns:
            str: New task ID
        """
        tasks = self.load_tasks()

        # Generate task ID
        task_num = len(tasks) + 1
        task_id = f"task_{task_num:03d}"

        # Create task
        task = {
            'id': task_id,
            'prompt': prompt,
            'status': 'pending',
            'priority': priority,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # Add optional fields
        if system:
            task['system'] = system
        if max_tokens:
            task['max_tokens'] = max_tokens
        if model:
            task['model'] = model

        tasks.append(task)
        self._save_tasks(tasks)

        return task_id

    def get_task_by_id(self, task_id):
        """
        Get task by ID

        Args:
            task_id: Task ID to find

        Returns:
            dict: Task or None if not found
        """
        tasks = self.load_tasks()

        for task in tasks:
            if task['id'] == task_id:
                return task

        return None

    def get_task_by_worker(self, worker_name):
        """
        Get currently assigned task for worker

        Args:
            worker_name: Worker name

        Returns:
            dict: Assigned task or None
        """
        tasks = self.load_tasks()

        for task in tasks:
            if task.get('assigned_to') == worker_name and task['status'] == 'assigned':
                return task

        return None


def validate_task(task):
    """
    Validate task structure and values

    Args:
        task: Task dictionary to validate

    Returns:
        str: Error message or None if valid
    """
    # Check required fields
    if 'id' not in task:
        return "Missing required field: 'id'"

    if 'prompt' not in task:
        return "Missing required field: 'prompt'"

    # Validate optional model field
    if 'model' in task:
        model = task['model']
        if not config.validate_model(model):
            return f"Invalid model: {model}. Valid models: {', '.join(config.VALID_MODELS)}"

    # Validate optional max_tokens field
    if 'max_tokens' in task:
        max_tokens = task['max_tokens']
        model = task.get('model', config.DEFAULT_MODEL)

        if not config.validate_max_tokens(max_tokens, model):
            return f"Invalid max_tokens: {max_tokens} for model {model}"

    # Validate priority
    if 'priority' in task:
        priority = task['priority']
        if not isinstance(priority, int) or priority < 1 or priority > 5:
            return "Priority must be integer between 1 and 5"

    return None
