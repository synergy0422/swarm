---
phase: 02-tmux-integration
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - /home/user/AAA/swarm/swarm/tmux_manager.py
  - /home/user/AAA/swarm/swarm/exceptions.py
  - /home/user/AAA/swarm/tests/test_tmux_manager.py
autonomous: true
user_setup:
  - "Install tmux: sudo apt install tmux (or brew install tmux)"
  - "Install libtmux: pip install libtmux"

must_haves:
  truths:
    - "TmuxSwarmManager can spawn agents in tmux panes"
    - "Agent output can be streamed in real-time"
    - "All paths use os.path.join with AI_SWARM_DIR"
    - "API key only from env vars (no .env loading)"
  artifacts:
    - path: "/home/user/AAA/swarm/swarm/tmux_manager.py"
      provides: "TmuxSwarmManager class for tmux pane management"
    - path: "/home/user/AAA/swarm/swarm/exceptions.py"
      provides: "Custom exceptions for tmux operations"
  key_links:
    - from: "tmux_manager.py"
      to: "task_queue.py"
      via: "Both use AI_SWARM_DIR for data directory"
      pattern: "AI_SWARM_DIR"
---
<objective>
Implement tmux integration layer using libtmux to enable parallel agent execution in tmux panes.

Purpose: Allow Master to spawn AI agents in isolated tmux panes and stream their output in real-time.

Output:
- TmuxSwarmManager class with agent spawning, output streaming, and lifecycle management
- Custom exceptions for tmux operations
- Unit tests with mocked tmux
</objective>

<execution_context>
@/home/user/AAA/swarm/.planning/research/tmux-integration.md

Based on research, use libtmux library with:
- TmuxSwarmManager class for session/pane management
- AgentPane dataclass for tracking agent state
- AgentStatus enum for status tracking
- Async methods for streaming output
</context>

<tasks>

<task type="auto">
  <name>Create exceptions module for tmux operations</name>
  <files>
    /home/user/AAA/swarm/swarm/exceptions.py
  </files>
  <action>
    Create /home/user/AAA/swarm/swarm/exceptions.py with custom exceptions:

    ```python
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
    ```

    Keep it minimal - only what's needed for tmux operations.
  </action>
  <verify>
    python -c "from swarm.exceptions import TmuxSwarmError, SessionNotFoundError; print('OK')"
  </verify>
  <done>
    /home/user/AAA/swarm/swarm/exceptions.py exists with TmuxSwarmError hierarchy
  </done>
</task>

<task type="auto">
  <name>Implement TmuxSwarmManager core class</name>
  <files>
    /home/user/AAA/swarm/swarm/tmux_manager.py
  </files>
  <action>
    Create /home/user/AAA/swarm/swarm/tmux_manager.py with TmuxSwarmManager class.

    **CRITICAL CONSTRAINTS (must follow from Phase 1):**
    1. API Key only from env vars - NO dotenv loading
    2. Auto-create data directory with os.makedirs(exist_ok=True)
    3. Use os.environ.get('AI_SWARM_DIR', '/tmp/ai_swarm/') for data_dir
    4. Use os.path.join for all path construction

    **Implementation Requirements:**

    1. Imports:
       - from typing import Optional, Dict, List, AsyncIterator
       - from dataclasses import dataclass
       - from enum import Enum
       - import libtmux
       - import asyncio
       - import os

    2. AgentStatus Enum:
       - PENDING, RUNNING, STOPPED, FAILED, UNKNOWN

    3. AgentPane dataclass with agent_id, pane_id, window_id, session_id, pane, status

    4. TmuxSwarmManager class with:
       - __init__(cluster_id, base_dir=None, socket_path=None)
       - async start() - create tmux session
       - async shutdown(graceful=True) - cleanup all
       - async spawn_agent(agent_id, command, env=None) - create agent pane
       - async kill_agent(agent_id, graceful=True) - stop agent
       - async stream_agent_output(agent_id, poll_interval=0.1) - async iterator
       - async capture_agent_output(agent_id) - get all output
       - async broadcast(message) - send to all agents
       - async send_to_agent(agent_id, message) - send to specific agent
       - list_agents() -> List[str]
       - get_session_info() -> Dict

    5. In start(), create session with:
       - session_name=f"swarm-{self.cluster_id}"
       - start_directory=self.base_dir
       - attach=False (critical - don't block)

    6. In spawn_agent(), create window with window_name=f"agent-{agent_id}"

    7. Store session data in AI_SWARM_DIR:
       - self.data_dir = os.environ.get('AI_SWARM_DIR', '/tmp/ai_swarm/')
       - os.makedirs(self.data_dir, exist_ok=True)
       - Use os.path.join(self.data_dir, 'swarm_sessions.json') for session tracking

    8. Add pre-flight check in start():
       - Verify tmux is installed (subprocess check)
  </action>
  <verify>
    python -c "from swarm.tmux_manager import TmuxSwarmManager, AgentStatus, AgentPane; print('OK')"
    grep -n "AI_SWARM_DIR\|os.makedirs\|os.path.join" /home/user/AAA/swarm/swarm/tmux_manager.py | head -5
    grep -E "dotenv|load_dotenv" /home/user/AAA/swarm/swarm/tmux_manager.py || echo "No dotenv - PASS"
  </verify>
  <done>
    TmuxSwarmManager class with all required methods
    Uses AI_SWARM_DIR env var (default /tmp/ai_swarm/)
    Auto-creates data directory with os.makedirs(exist_ok=True)
    Uses os.path.join for all path construction
    No dotenv or .env loading
  </done>
</task>

<task type="auto">
  <name>Write unit tests for tmux manager</name>
  <files>
    /home/user/AAA/swarm/tests/test_tmux_manager.py
  </files>
  <action>
    Create /home/user/AAA/swarm/tests/test_tmux_manager.py with mocked tmux tests.

    **Test Isolation Requirements (from Phase 1):**
    - Use AI_SWARM_DIR env var with temp directory
    - Tests must be repeatable with pytest -q

    **Tests to include:**

    1. Test imports work correctly
       - from swarm import tmux_manager, exceptions
       - Verify classes can be instantiated

    2. Test AgentStatus enum values
       - Verify all expected statuses exist

    3. Test AgentPane dataclass creation
       - Verify required fields

    4. Test TmuxSwarmManager initialization
       - Verify default values
       - Verify data_dir is set correctly from AI_SWARM_DIR

    5. Test tmux availability check (mocked)
       - Verify tmux not installed handling

    6. Test session info structure
       - Verify get_session_info returns expected keys

    7. Test list_agents returns empty list initially

    **Use unittest.mock for libtmux:**
    ```python
    from unittest.mock import patch, MagicMock
    import libtmux

    @pytest.fixture
    def mock_tmux():
        with patch.object(libtmux, 'Server') as mock_server:
            yield mock_server
    ```

    **conftest.py update:**
    - Ensure isolated_swarm_dir fixture is available
  </action>
  <verify>
    python -c "from tests.test_tmux_manager import *; print('Import OK')"
    pytest -q /home/user/AAA/swarm/tests/test_tmux_manager.py --tb=short 2>&1 | tail -10
  </verify>
  <done>
    test_tmux_manager.py exists with mocked unit tests
    Tests pass with pytest -q
    Tests use isolated_swarm_dir fixture
  </done>
</task>

<task type="auto">
  <name>Update package __init__.py exports</name>
  <files>
    /home/user/AAA/swarm/swarm/__init__.py
  </files>
  <action>
    Update /home/user/AAA/swarm/swarm/__init__.py to export new classes:

    ```python
    from swarm.config import Config
    from swarm.task_queue import TaskQueue
    from swarm.worker_smart import WorkerSmart
    from swarm.tmux_manager import TmuxSwarmManager, AgentStatus, AgentPane
    from swarm.exceptions import TmuxSwarmError

    __all__ = [
        'Config',
        'TaskQueue',
        'WorkerSmart',
        'TmuxSwarmManager',
        'AgentStatus',
        'AgentPane',
        'TmuxSwarmError',
    ]
    ```

    Keep version constant and __version__ as is.
  </action>
  <verify>
    python -c "from swarm import TmuxSwarmManager, AgentStatus, AgentPane, TmuxSwarmError; print('All exports OK')"
  </verify>
  <done>
    swarm/__init__.py exports TmuxSwarmManager, AgentStatus, AgentPane, TmuxSwarmError
  </done>
</task>

</tasks>

<verification>
1. TmuxSwarmManager class works:
   python -c "from swarm.tmux_manager import TmuxSwarmManager; m = TmuxSwarmManager('test'); print(m.data_dir)"

2. Path configuration:
   grep -r "AI_SWARM_DIR" /home/user/AAA/swarm/swarm/tmux_manager.py

3. Tests pass:
   pytest -q /home/user/AAA/swarm/tests/test_tmux_manager.py -v

4. No dotenv loading:
   grep -E "dotenv|load_dotenv" /home/user/AAA/swarm/swarm/*.py || echo "No dotenv - PASS"
</verification>

<success_criteria>
- [ ] TmuxSwarmManager class implemented with all core methods
- [ ] exceptions.py created with TmuxSwarmError hierarchy
- [ ] test_tmux_manager.py created with mocked tests
- [ ] swarm/__init__.py updated to export new classes
- [ ] Tests pass: pytest -q /home/user/AAA/swarm/tests/test_tmux_manager.py returns 0
- [ ] AI_SWARM_DIR used consistently with os.path.join
- [ ] No dotenv loading anywhere
</success_criteria>

<output>
After completion, create `.planning/phases/02-tmux-integration/02-SUMMARY.md` with:
- Frontmatter: phase, plan, completed, timestamp, files_created, tests_run
- Summary of changes made
- Test results
- Any issues encountered
</output>
