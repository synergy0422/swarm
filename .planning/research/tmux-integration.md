# Tmux Integration Research for AI Swarm System

## Overview

This document outlines the research findings for implementing tmux integration in the AI Swarm system, enabling multiple AI agents to run in parallel tmux panes coordinated by a Master node.

---

## 1. Library Recommendation

### Primary Choice: libtmux

**libtmux** (`/tmux-python/libtmux`) is the recommended library for tmux integration. It provides a comprehensive Python API for tmux automation with 90+ code examples and active maintenance.

#### Why libtmux:

| Criteria | libtmux | tmuxp | teamocil |
|----------|---------|-------|----------|
| **Control Level** | Full programmatic control | Configuration-based | Configuration-based |
| **Dynamic Creation** | Excellent (create at runtime) | Limited (predefined config) | Limited (predefined config) |
| **Output Capture** | Yes (`capture-pane`) | No | No |
| **Async Support** | Possible with threading | No | No |
| **Maintenance** | Active (tmux-python org) | Active | Less active |
| **Learning Curve** | Moderate | Low | Low |

#### Installation:

```bash
pip install libtmux
```

#### Key Features for Swarm System:

```python
import libtmux

# Server-level operations
server = libtmux.Server()
# Server(socket_path=/tmp/tmux-.../default)

# Session management
session = server.new_session(
    session_name="swarm-master",
    start_directory="/home/user/AAA/swarm",
    attach=False  # Critical: don't block
)

# Window and pane creation
window = session.new_window(
    window_name="agent-1",
    attach=False
)
pane = window.split(attach=False)

# Send commands
pane.send_keys("python agent.py --id=1", enter=True)

# Capture output
output = pane.cmd('capture-pane', '-p').stdout

# Cleanup
pane.kill()  # or window.kill() or session.kill_session()
```

---

## 2. Architecture Overview

### How Tmux Integration Fits in the Swarm System

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Swarm Architecture                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐    ┌─────────────────────────────────┐     │
│  │   Master    │───>│        Tmux Integration         │     │
│  │  Dispatcher │    │                                 │     │
│  └─────────────┘    │  ┌───────────────────────────┐  │     │
│       │             │  │  Server (single tmux srv) │  │     │
│       │             │  └───────────────────────────┘  │     │
│       │             │            │                     │     │
│       │             │            ▼                     │     │
│       │             │  ┌───────────────────────────┐  │     │
│       │             │  │ Session: "swarm-cluster"  │  │     │
│       │             │  │                           │  │     │
│       │             │  │  ┌─────┐ ┌─────┐ ┌─────┐  │  │     │
│       │             │  │  │Win-1│ │Win-2│ │Win-N│  │  │     │
│       │             │  │  └─────┘ └─────┘ └─────┘  │  │     │
│       │             │  │     │       │       │     │  │     │
│       │             │  │     ▼       ▼       ▼     │  │     │
│       │             │  │  ┌─────┐ ┌─────┐ ┌─────┐  │  │     │
│       │             │  │  │Pane │ │Pane │ │Pane │  │  │     │
│       │             │  │  │ 0-1 │ │ 0-2 │ │ 0-n │  │  │     │
│       │             │  │  └─────┘ └─────┘ └─────┘  │  │     │
│       │             │  └───────────────────────────┘  │     │
│       │             └─────────────────────────────────┘     │
│       │                           │                          │
│       ▼                           ▼                          │
│  ┌─────────────┐         ┌─────────────────────┐            │
│  │ Task Queue  │<───────>│  Pane Output Stream │            │
│  └─────────────┘         └─────────────────────┘            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Single Server**: One tmux server per swarm instance
2. **One Session per Swarm**: `swarm-{cluster_id}` naming convention
3. **One Window per Agent**: Window name = agent_id
4. **Single Pane per Window**: Each agent gets one pane (simplifies management)
5. **Background Execution**: All panes created with `attach=False`

---

## 3. Key Implementation Patterns

### 3.1 Creating a Session with Multiple Agent Panes

```python
import libtmux
from typing import List, Dict

class TmuxManager:
    def __init__(self, session_name: str, base_dir: str = None):
        self.server = libtmux.Server()
        self.session_name = session_name
        self.base_dir = base_dir

    def create_swarm_session(self, agent_ids: List[str]) -> Dict[str, Dict]:
        """
        Create a swarm session with one window/pane per agent.
        Returns mapping of agent_id -> pane_info.
        """
        # Create the main session
        session = self.server.new_session(
            session_name=self.session_name,
            start_directory=self.base_dir,
            attach=False
        )

        agent_panes = {}

        for i, agent_id in enumerate(agent_ids):
            if i == 0:
                # First agent uses the default pane
                window = session.active_window
            else:
                # Subsequent agents get new windows
                window = session.new_window(
                    window_name=f"agent-{agent_id}",
                    attach=False
                )

            # Optional: split for additional panes (if needed)
            # pane = window.split(attach=False)

            agent_panes[agent_id] = {
                'session_id': session.get('session_id'),
                'window_id': window.get('window_id'),
                'pane_id': window.active_pane.get('pane_id'),
                'window_name': window.get('window_name'),
            }

        return agent_panes
```

### 3.2 Spawning Agent Processes in Panes

```python
import libtmux

def spawn_agent_in_pane(pane: libtmux.Pane, agent_id: str, config: dict):
    """
    Spawn an agent process in a tmux pane.
    """
    # Set pane title for easy identification
    pane.cmd('select-pane', '-T', f'Agent-{agent_id}')

    # Change to base directory
    pane.send_keys(f'cd {config["work_dir"]}', enter=True)

    # Set environment variables
    pane.send_keys(f'export AGENT_ID={agent_id}', enter=True)
    pane.send_keys(f'export SWARM_MASTER={config["master_url"]}', enter=True)

    # Start the agent (assuming it's a Python script)
    cmd = f'python -m agents.run --id={agent_id} --master={config["master_url"]}'
    pane.send_keys(cmd, enter=True)

    return pane
```

### 3.3 Capturing Pane Output (Batch Mode)

```python
def capture_pane_output(pane: libtmux.Pane, timeout: int = 5) -> str:
    """
    Capture output from a pane with timeout.
    Note: This is batch capture, not streaming.
    """
    # Clear pane history first if needed
    # pane.clear()

    # Capture the visible pane content
    result = pane.cmd('capture-pane', '-p', '-S', f'-{timeout}')

    if result.stdout:
        return '\n'.join(result.stdout)
    return ''

def get_new_output(pane: libtmux.Pane, last_line: int = None) -> str:
    """
    Get only new output since last capture.
    Uses capture-pane with line range.
    """
    if last_line is None:
        # Get all output
        result = pane.cmd('capture-pane', '-p')
    else:
        # Get output from last_line onwards
        result = pane.cmd('capture-pane', '-p', '-S', str(last_line))

    if result.stdout:
        lines = result.stdout
        return '\n'.join(lines)
    return ''
```

### 3.4 Real-Time Streaming Output (Polling Approach)

```python
import time
from collections import deque

class PaneStream:
    """
    Real-time output streaming from a tmux pane.
    Uses polling to detect new output.
    """

    def __init__(self, pane: libtmux.Pane, poll_interval: float = 0.1):
        self.pane = pane
        self.poll_interval = poll_interval
        self.last_line = -1
        self.lines = deque()

    def read_new(self) -> List[str]:
        """
        Read new lines since last check.
        Returns list of new lines.
        """
        # Get current pane content
        result = self.pane.cmd('capture-pane', '-p', '-e')
        if not result.stdout:
            return []

        # Find lines we haven't seen
        all_lines = result.stdout
        new_lines = []

        # Simple approach: get last N lines and diff
        # More sophisticated: track line numbers with capture-pane -S
        for line in all_lines[self.last_line + 1:]:
            new_lines.append(line)

        self.last_line = len(all_lines) - 1
        return new_lines

    def stream(self, callback, duration: float = None):
        """
        Stream output to a callback function.
        """
        start_time = time.time()
        while True:
            new_lines = self.read_new()
            for line in new_lines:
                callback(line)

            if duration and (time.time() - start_time) > duration:
                break
            time.sleep(self.poll_interval)

# Usage example
def log_output(line):
    print(f"[{time.strftime('%H:%M:%S')}] {line}", flush=True)

stream = PaneStream(pane)
stream.stream(log_output, duration=30)
```

### 3.5 Pane Lifecycle Management

```python
class PaneLifecycle:
    """
    Manages pane lifecycle with health checks and cleanup.
    """

    def __init__(self, pane: libtmux.Pane, agent_id: str):
        self.pane = pane
        self.agent_id = agent_id
        self.start_time = time.time()
        self.is_alive = True

    def check_health(self) -> Dict:
        """
        Check if the agent pane is healthy.
        """
        try:
            # Try to capture pane - if it fails, pane is dead
            output = self.pane.cmd('capture-pane', '-p', '-e')

            # Check if pane still exists
            pane_info = self.pane.cmd('display-message', '-p', '#{pane_id}')
            is_alive = pane_info.returncode == 0

            return {
                'alive': is_alive,
                'uptime': time.time() - self.start_time,
                'output_available': bool(output.stdout)
            }
        except Exception as e:
            return {
                'alive': False,
                'error': str(e)
            }

    def kill(self):
        """
        Gracefully or forcefully kill the pane.
        """
        # Try graceful shutdown first
        self.pane.send_keys('SIGTERM', enter=True)
        time.sleep(2)

        # Check if still alive
        health = self.check_health()
        if health['alive']:
            # Force kill
            self.pane.cmd('kill-pane')

        self.is_alive = False

    def cleanup_session(self, session: libtmux.Session):
        """
        Clean up entire session on shutdown.
        """
        session.kill_session()
```

### 3.6 Coordinating Multiple Panes

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class SwarmCoordinator:
    """
    Coordinates multiple agent panes.
    """

    def __init__(self, server: libtmux.Server, max_workers: int = 5):
        self.server = server
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.panes = {}  # agent_id -> pane mapping
        self.status = {}  # agent_id -> status

    async def send_broadcast(self, message: str):
        """
        Send a message to all agent panes.
        """
        loop = asyncio.get_event_loop()
        await asyncio.gather(*[
            loop.run_in_executor(
                self.executor,
                self._send_to_pane,
                agent_id,
                message
            )
            for agent_id in self.panes
        ])

    def _send_to_pane(self, agent_id: str, message: str):
        """
        Send message to a specific pane.
        """
        pane = self.panes.get(agent_id)
        if pane:
            pane.send_keys(message, enter=True)

    async def gather_outputs(self, timeout: float = 10) -> Dict[str, str]:
        """
        Gather output from all panes with timeout.
        """
        loop = asyncio.get_event_loop()
        tasks = {
            agent_id: loop.run_in_executor(
                self.executor,
                capture_pane_output,
                pane
            )
            for agent_id, pane in self.panes.items()
        }

        results = {}
        for agent_id, future in asyncio.as_completed(tasks.items()):
            try:
                results[agent_id] = await asyncio.wait_for(
                    future,
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                results[agent_id] = "TIMEOUT"

        return results

    async def wait_for_condition(
        self,
        condition_fn,
        timeout: float = 30,
        poll_interval: float = 0.5
    ) -> bool:
        """
        Wait until condition function returns True for all agents.
        """
        start = time.time()
        while time.time() - start < timeout:
            if all(condition_fn(agent_id) for agent_id in self.panes):
                return True
            await asyncio.sleep(poll_interval)
        return False
```

---

## 4. API Design Suggestions

### Proposed Module Structure

```
/home/user/AAA/swarm/swarm/
    core/
        tmux_manager.py      # Main tmux integration
    types/
        tmux_types.py        # Type definitions
    exceptions/
        tmux_exceptions.py   # Custom exceptions
```

### Core API Design

```python
# swarm/core/tmux_manager.py

from typing import Optional, Dict, List, Callable, AsyncIterator
from dataclasses import dataclass
from enum import Enum
import libtmux


class AgentStatus(Enum):
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
    pane: libtmux.Pane  # Reference to actual pane
    status: AgentStatus = AgentStatus.PENDING


class TmuxSwarmManager:
    """
    Manages tmux sessions for the AI Swarm system.

    Usage:
        manager = TmuxSwarmManager("swarm-cluster-1")
        await manager.start()

        # Add agents
        await manager.spawn_agent("agent-1", config)
        await manager.spawn_agent("agent-2", config)

        # Stream output
        async for line in manager.stream_agent_output("agent-1"):
            print(line)

        # Cleanup
        await manager.shutdown()
    """

    def __init__(
        self,
        cluster_id: str,
        base_dir: str = None,
        socket_path: str = None
    ):
        self.cluster_id = cluster_id
        self.base_dir = base_dir
        self.socket_path = socket_path

        # Connection
        if socket_path:
            self.server = libtmux.Server(socket_path=socket_path)
        else:
            self.server = libtmux.Server()

        # Session tracking
        self._session: Optional[libtmux.Session] = None
        self._agents: Dict[str, AgentPane] = {}

    # ==================== Lifecycle ====================

    async def start(self) -> None:
        """Initialize the swarm session."""
        self._session = self.server.new_session(
            session_name=f"swarm-{self.cluster_id}",
            start_directory=self.base_dir,
            attach=False
        )

    async def shutdown(self, graceful: bool = True) -> None:
        """Shutdown the swarm and cleanup all resources."""
        if self._session:
            if graceful:
                # Send shutdown signal to all agents first
                for agent in self._agents.values():
                    agent.pane.send_keys('shutdown', enter=True)
                    await asyncio.sleep(1)

            self._session.kill_session()
            self._session = None
            self._agents.clear()

    # ==================== Agent Management ====================

    async def spawn_agent(
        self,
        agent_id: str,
        command: str,
        env: Dict[str, str] = None
    ) -> AgentPane:
        """
        Spawn an agent in a new tmux pane.

        Args:
            agent_id: Unique identifier for the agent
            command: Command to execute
            env: Environment variables

        Returns:
            AgentPane object
        """
        # Create new window for this agent
        window = self._session.new_window(
            window_name=f"agent-{agent_id}",
            attach=False
        )

        # Get the active pane
        pane = window.active_pane

        # Set pane title
        pane.cmd('select-pane', '-T', agent_id)

        # Set environment if provided
        if env:
            for key, value in env.items():
                pane.send_keys(f'export {key}={value}', enter=True)

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
        """
        agent = self._agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        if graceful:
            agent.pane.send_keys('SIGTERM', enter=True)
            await asyncio.sleep(2)

        # Force kill if still alive
        try:
            agent.pane.cmd('display-message', '-p', '#{pane_id}')
            agent.pane.cmd('kill-pane')
        except Exception:
            pass  # Pane already dead

        agent.status = AgentStatus.STOPPED
        del self._agents[agent_id]

    def get_agent_status(self, agent_id: str) -> AgentStatus:
        """Get the status of an agent."""
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

        Yields:
            Lines of output from the agent
        """
        agent = self._agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

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
        """
        agent = self._agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        result = agent.pane.cmd('capture-pane', '-p')
        return '\n'.join(result.stdout) if result.stdout else ''

    # ==================== Broadcast & Control ====================

    async def broadcast(self, message: str) -> None:
        """
        Send a message to all agents.
        """
        for agent in self._agents.values():
            agent.pane.send_keys(message, enter=True)

    async def send_to_agent(self, agent_id: str, message: str) -> None:
        """
        Send a message to a specific agent.
        """
        agent = self._agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        agent.pane.send_keys(message, enter=True)

    # ==================== Session Info ====================

    def list_agents(self) -> List[str]:
        """List all agent IDs."""
        return list(self._agents.keys())

    def get_session_info(self) -> Dict:
        """Get information about the current session."""
        if not self._session:
            return {'active': False}

        return {
            'active': True,
            'session_id': self._session.get('session_id'),
            'session_name': self._session.get('session_name'),
            'windows': len(self._session.windows),
            'agent_count': len(self._agents),
        }
```

### Exception Definitions

```python
# swarm/exceptions/tmux_exceptions.py

class TmuxSwarmError(Exception):
    """Base exception for tmux swarm errors."""
    pass


class SessionNotFoundError(TmuxSwarmError):
    """Raised when a session is not found."""
    pass


class AgentNotFoundError(TmuxSwarmError):
    """Raised when an agent is not found."""
    pass


class PaneDeadError(TmuxSwarmError):
    """Raised when a pane is no longer alive."""
    pass


class SessionCreationError(TmuxSwarmError):
    """Raised when session creation fails."""
    pass


class CommandTimeoutError(TmuxSwarmError):
    """Raised when a command times out."""
    pass
```

---

## 5. Risks and Considerations

### 5.1 Technical Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Tmux not installed** | High | Check `which tmux` before initialization |
| **Socket path issues** | Medium | Use `TMUX_TMPDIR` for custom sockets |
| **Pane hanging on output** | Medium | Use timeouts on capture operations |
| **Session orphaned** | High | Implement cleanup on process exit (atexit) |
| **Race conditions** | Medium | Use locks for concurrent pane access |
| **Output truncation** | Low | Increase pane history limit (`history-limit`) |

### 5.2 Configuration Considerations

```python
# Recommended tmux settings for swarm use
TMUX_CONF = """
# Increase history for better output capture
set -g history-limit 10000

# Faster command execution
set -g escape-time 50

# Don't automatically rename windows
set -g automatic-rename off

# Enable mouse mode for debugging (optional)
# set -g mouse on
"""

# Apply via pane.send_keys or .tmux.conf
```

### 5.3 Environment Considerations

```python
import os

# Custom tmux socket path for isolation
os.environ['TMUX_TMPDIR'] = '/tmp/swarm-tmux'

# Or specify socket name directly
server = libtmux.Server(socket_name='swarm-main')
```

### 5.4 Edge Cases

1. **Agent Process Dies but Pane Stays**: Monitor pane content, not just existence
2. **Infinite Output Loop**: Implement rate limiting or output size caps
3. **Slow Pane Creation**: Use `attach=False` to avoid blocking
4. **Window/Pane Naming Conflicts**: Use unique IDs, not human-readable names
5. **Signal Handling**: Ensure proper SIGTERM/SIGKILL handling
6. **Network Recovery**: Agents may need to reconnect to Master

### 5.5 Performance Considerations

- **Polling Overhead**: `capture-pane` has some overhead; use 100ms+ intervals
- **Memory Growth**: Large outputs accumulate in pane history; clear periodically
- **Concurrent Captures**: Avoid capturing same pane from multiple threads
- **Socket Contention**: High-frequency operations may contend for socket

### 5.6 Alternative Approaches to Consider

1. **Direct subprocess with PTY**: More control, no tmux dependency
   - Libraries: `pty`, `pexpect`, `pyte`

2. **SSH-based Remote Execution**: For distributed agents
   - Libraries: `paramiko`, `asyncssh`

3. **Docker Containers**: Better isolation, harder to debug
   - Libraries: `docker-py`, `asyncio-docker`

4. **Message Queue + Workers**: No tmux needed
   - Libraries: `redis`, `rabbitmq`, `celery`

---

## 6. Quick Start Implementation Plan

### Phase 2 Tasks (Suggested)

1. **Create basic TmuxSwarmManager class** (libtmux-based)
2. **Implement agent spawning** with environment variable support
3. **Add output streaming** with polling-based approach
4. **Implement health checking** for agent panes
5. **Add graceful shutdown** with signal handling
6. **Write integration tests** with mocked tmux

### Example Usage (Final Goal)

```python
import asyncio
from swarm.core.tmux_manager import TmuxSwarmManager

async def main():
    # Initialize
    manager = TmuxSwarmManager(
        cluster_id="test-cluster",
        base_dir="/home/user/AAA/swarm"
    )
    await manager.start()

    # Spawn agents
    await manager.spawn_agent(
        "agent-1",
        "python -m agents.worker --id=1"
    )
    await manager.spawn_agent(
        "agent-2",
        "python -m agents.worker --id=2"
    )

    # Stream output
    async for line in manager.stream_agent_output("agent-1"):
        print(f"[agent-1] {line}")

    # Broadcast
    await manager.broadcast("status")

    # Cleanup
    await manager.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Sources

- [libtmux GitHub Repository](https://github.com/tmux-python/libtmux)
- [libtmux Quickstart Documentation](https://github.com/tmux-python/libtmux/blob/master/docs/quickstart.md)
- [libtmux Context Managers](https://github.com/tmux-python/libtmux/blob/master/docs/topics/context_managers.md)
- [tmuxp Configuration Documentation](https://github.com/tmux-python/tmuxp)
- [Teamocil YAML Configuration](https://github.com/remi/teamocil)
