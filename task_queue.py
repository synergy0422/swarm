#!/usr/bin/env python3
"""
Task Queue Manager for AI Swarm System

 DEPRECATED: This module is a thin wrapper for backwards compatibility.
 Use `from swarm import task_queue` instead.
"""

# Re-export from swarm package for backwards compatibility
from swarm.task_queue import TaskQueue, validate_task

__all__ = ['TaskQueue', 'validate_task']
