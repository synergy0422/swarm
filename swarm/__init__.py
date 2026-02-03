"""
AI Swarm - Multi-Agent Task Processing System

A distributed multi-agent system where a Master coordinates multiple Worker nodes
to process tasks in parallel using Anthropic's Claude API.
"""

from swarm.task_queue import TaskQueue
from swarm.worker_smart import SmartWorker
from swarm.tmux_manager import TmuxSwarmManager, AgentStatus, AgentPane
from swarm.exceptions import TmuxSwarmError
from swarm.status_broadcaster import StatusBroadcaster, BroadcastState
from swarm.task_lock import TaskLockManager, LockInfo
from swarm.master_scanner import MasterScanner, WorkerStatus, create_scanner
from swarm.auto_rescuer import (
    AutoRescuer,
    AUTO_ENTER_PATTERNS,
    MANUAL_CONFIRM_PATTERNS,
    DANGEROUS_PATTERNS,
    ENV_AUTO_RESCUE_COOLING,
    ENV_AUTO_RESCUE_DRY_RUN,
    DEFAULT_COOLING_TIME,
)
from swarm.master_dispatcher import (
    MasterDispatcher,
    TaskInfo,
    DispatchResult,
    create_dispatcher,
)

__all__ = [
    # Core
    'TaskQueue',
    'SmartWorker',
    'TmuxSwarmManager',
    'AgentStatus',
    'AgentPane',
    'TmuxSwarmError',
    'StatusBroadcaster',
    'BroadcastState',
    'TaskLockManager',
    'LockInfo',
    # Master (Phase 4)
    'MasterScanner',
    'WorkerStatus',
    'create_scanner',
    'AutoRescuer',
    'AUTO_ENTER_PATTERNS',
    'MANUAL_CONFIRM_PATTERNS',
    'DANGEROUS_PATTERNS',
    'ENV_AUTO_RESCUE_COOLING',
    'ENV_AUTO_RESCUE_DRY_RUN',
    'DEFAULT_COOLING_TIME',
    'MasterDispatcher',
    'TaskInfo',
    'DispatchResult',
    'create_dispatcher',
    # CLI (Phase 5) - cli module accessible via explicit import only
]

__version__ = "0.1.0"
