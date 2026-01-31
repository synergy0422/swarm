"""
AI Swarm - Multi-Agent Task Processing System

A distributed multi-agent system where a Master coordinates multiple Worker nodes
to process tasks in parallel using Anthropic's Claude API.
"""

from swarm.task_queue import TaskQueue
from swarm.worker_smart import SmartWorker
from swarm.tmux_manager import TmuxSwarmManager, AgentStatus, AgentPane
from swarm.exceptions import TmuxSwarmError

__all__ = [
    'TaskQueue',
    'SmartWorker',
    'TmuxSwarmManager',
    'AgentStatus',
    'AgentPane',
    'TmuxSwarmError',
]

__version__ = "0.1.0"
