"""
Tmux integration layer for AI Swarm using libtmux.

Provides TmuxSwarmManager for managing tmux sessions with agent panes.
"""

from typing import Optional, Dict, List, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
import libtmux
import asyncio
import os
import shlex

from swarm.exceptions import (
    TmuxSwarmError,
    SessionNotFoundError,
    AgentNotFoundError,
    PaneDeadError,
    SessionCreationError
)


class AgentStatus(Enum):
    """Status of an agent in a tmux pane."""
    PENDING = "pending"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class AgentPane:
    """Represents an agent running in a tmux pane."""
    agent_id: str
    pane_id: str
    window_id: str
    session_id: str
    pane: object  # libtmux.Pane reference
    status: AgentStatus = AgentStatus.PENDING


class TmuxSwarmManager:
    """
    Manages tmux sessions for the AI Swarm system.

    Usage:
        manager = TmuxSwarmManager("swarm-cluster-1")
        await manager.start()

        # Add agents
        await manager.spawn_agent("agent-1", "python agent.py")
        await manager.spawn_agent("agent-2", "python agent.py")

        # Stream output
        async for line in manager.stream_agent_output("agent-1"):
            print(line)

        # Cleanup
        await manager.shutdown()
    """

    def __init__(
        self,
        cluster_id: str,
        base_dir: Optional[str] = None,
        socket_path: Optional[str] = None
    ):
        """
        Initialize the TmuxSwarmManager.

        Args:
            cluster_id: Unique identifier for the swarm cluster
            base_dir: Base directory for tmux sessions (defaults to current dir)
            socket_path: Optional custom tmux socket path
        """
        self.cluster_id = cluster_id
        self.base_dir = base_dir or os.getcwd()
        self.socket_path = socket_path

        # Initialize tmux server
        if socket_path:
            self.server = libtmux.Server(socket_path=socket_path)
        else:
            self.server = libtmux.Server()

        # Session tracking
        self._session: Optional[libtmux.Session] = None
        self._agents: Dict[str, AgentPane] = {}

        # Data directory for session tracking (follows Phase 1 conventions)
        self.data_dir = os.environ.get('AI_SWARM_DIR', '/tmp/ai_swarm/')
        os.makedirs(self.data_dir, exist_ok=True)

    # ==================== Lifecycle ====================

    async def start(self) -> None:
        """
        Initialize the swarm session with tmux pre-flight check.

        Raises:
            SessionCreationError: If tmux is not installed or session creation fails
        """
        # Pre-flight check: verify tmux is installed
        import subprocess
        try:
            subprocess.run(
                ['tmux', '-V'],
                capture_output=True,
                check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise SessionCreationError(
                "tmux is not installed. Install with: sudo apt install tmux"
            )

        # Create the swarm session
        self._session = self.server.new_session(
            session_name=f"swarm-{self.cluster_id}",
            start_directory=self.base_dir,
            attach=False  # Critical: don't block
        )

    async def shutdown(self, graceful: bool = True) -> None:
        """
        Shutdown the swarm and cleanup all resources.

        Args:
            graceful: If True, send shutdown signal before killing
        """
        if self._session:
            if graceful:
                # Send shutdown signal to all agents first
                for agent in self._agents.values():
                    try:
                        agent.pane.send_keys('SIGTERM', enter=True)
                        await asyncio.sleep(0.5)
                    except Exception:
                        pass  # Pane already dead

            # Kill the session
            self._session.kill_session()
            self._session = None
            self._agents.clear()

    # ==================== Agent Management ====================

    async def spawn_agent(
        self,
        agent_id: str,
        command: str,
        env: Optional[Dict[str, str]] = None
    ) -> AgentPane:
        """
        Spawn an agent in a new tmux pane.

        Args:
            agent_id: Unique identifier for the agent
            command: Command to execute in the pane
            env: Optional environment variables to set

        Returns:
            AgentPane object representing the agent's pane

        Raises:
            SessionNotFoundError: If session is not active
        """
        if not self._session:
            raise SessionNotFoundError("Session not active. Call start() first.")

        # Create new window for this agent
        window = self._session.new_window(
            window_name=f"agent-{agent_id}",
            attach=False
        )

        # Get the active pane
        pane = window.active_pane

        # Set pane title for easy identification
        pane.cmd('select-pane', '-T', agent_id)

        # Set environment variables if provided
        # Use shlex.quote to safely escape values containing special characters
        if env:
            for key, value in env.items():
                safe_value = shlex.quote(value)
                pane.send_keys(f'export {key}={safe_value}', enter=True)

        # Send the startup command
        pane.send_keys(command, enter=True)

        # Track the agent
        agent_pane = AgentPane(
            agent_id=agent_id,
            pane_id=pane.get('pane_id'),
            window_id=window.get('window_id'),
            session_id=self._session.get('session_id'),
            pane=pane,
            status=AgentStatus.RUNNING
        )
        self._agents[agent_id] = agent_pane

        return agent_pane

    async def kill_agent(self, agent_id: str, graceful: bool = True) -> None:
        """
        Kill a specific agent.

        Args:
            agent_id: ID of the agent to kill
            graceful: If True, wait briefly before kill (tmux kill-pane is immediate)

        Raises:
            AgentNotFoundError: If agent is not found
        """
        agent = self._agents.get(agent_id)
        if not agent:
            raise AgentNotFoundError(f"Agent {agent_id} not found")

        # tmux doesn't support sending real signals via send_keys
        # Use kill-pane directly for reliable termination
        try:
            agent.pane.cmd('kill-pane')
        except Exception:
            pass  # Pane already dead

        agent.status = AgentStatus.STOPPED
        del self._agents[agent_id]

    def get_agent_status(self, agent_id: str) -> AgentStatus:
        """
        Get the status of an agent.

        Args:
            agent_id: ID of the agent to check

        Returns:
            AgentStatus of the agent or UNKNOWN if not found
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return AgentStatus.UNKNOWN

        try:
            # Check if pane is still responsive
            agent.pane.cmd('display-message', '-p', '#{pane_id}')
            return AgentStatus.RUNNING if agent.status == AgentStatus.RUNNING else agent.status
        except Exception:
            return AgentStatus.FAILED

    # ==================== Output Streaming ====================

    async def stream_agent_output(
        self,
        agent_id: str,
        poll_interval: float = 0.1
    ) -> AsyncIterator[str]:
        """
        Stream output from an agent's pane.

        Args:
            agent_id: ID of the agent to stream
            poll_interval: Polling interval in seconds

        Yields:
            Lines of output from the agent

        Raises:
            AgentNotFoundError: If agent is not found
        """
        agent = self._agents.get(agent_id)
        if not agent:
            raise AgentNotFoundError(f"Agent {agent_id} not found")

        last_line = -1

        while agent.status == AgentStatus.RUNNING:
            try:
                # Capture new output
                result = agent.pane.cmd('capture-pane', '-p', '-e')
                if result.stdout:
                    lines = result.stdout
                    for line in lines[last_line + 1:]:
                        yield line
                    last_line = len(lines) - 1
            except Exception:
                break

            await asyncio.sleep(poll_interval)

    async def capture_agent_output(self, agent_id: str) -> str:
        """
        Capture all current output from an agent's pane.

        Args:
            agent_id: ID of the agent to capture

        Returns:
            All current output from the pane

        Raises:
            AgentNotFoundError: If agent is not found
        """
        agent = self._agents.get(agent_id)
        if not agent:
            raise AgentNotFoundError(f"Agent {agent_id} not found")

        result = agent.pane.cmd('capture-pane', '-p')
        return '\n'.join(result.stdout) if result.stdout else ''

    # ==================== Broadcast & Control ====================

    async def broadcast(self, message: str) -> None:
        """
        Send a message to all agents.

        Args:
            message: Message to send to all agent panes
        """
        for agent in self._agents.values():
            agent.pane.send_keys(message, enter=True)

    async def send_to_agent(self, agent_id: str, message: str) -> None:
        """
        Send a message to a specific agent.

        Args:
            agent_id: ID of the agent to send to
            message: Message to send

        Raises:
            AgentNotFoundError: If agent is not found
        """
        agent = self._agents.get(agent_id)
        if not agent:
            raise AgentNotFoundError(f"Agent {agent_id} not found")

        agent.pane.send_keys(message, enter=True)

    # ==================== Session Info ====================

    def list_agents(self) -> List[str]:
        """List all agent IDs currently managed."""
        return list(self._agents.keys())

    def get_session_info(self) -> Dict:
        """
        Get information about the current session.

        Returns:
            Dict with session information including active status,
            session_id, session_name, window count, and agent count
        """
        if not self._session:
            return {'active': False}

        return {
            'active': True,
            'session_id': self._session.get('session_id'),
            'session_name': self._session.get('session_name'),
            'windows': len(self._session.windows),
            'agent_count': len(self._agents),
        }
