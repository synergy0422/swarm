---
phase: 01-project-initialization
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - /home/user/AAA/swarm/swarm/__init__.py
  - /home/user/AAA/swarm/swarm/config.py
  - /home/user/AAA/swarm/swarm/task_queue.py
  - /home/user/AAA/swarm/swarm/worker_smart.py
  - /home/user/AAA/swarm/scripts/__init__.py
  - /home/user/AAA/swarm/.env.example
  - /home/user/AAA/swarm/tests/__init__.py
  - /home/user/AAA/swarm/tests/conftest.py
autonomous: true
user_setup: []

must_haves:
  truths:
    - "API key is read from environment variable only"
    - "Task queue and worker use /tmp/ai_swarm/ for all file operations"
    - "Tests pass with pytest -q"
  artifacts:
    - path: "/home/user/AAA/swarm/swarm/__init__.py"
      provides: "Swarm package initialization"
    - path: "/home/user/AAA/swarm/swarm/config.py"
      provides: "Configuration module with env var priority"
    - path: "/home/user/AAA/swarm/swarm/task_queue.py"
      provides: "Task queue using /tmp/ai_swarm/"
    - path: "/home/user/AAA/swarm/swarm/worker_smart.py"
      provides: "Smart worker using /tmp/ai_swarm/"
    - path: "/home/user/AAA/swarm/.env.example"
      provides: "Environment variable template"
    - path: "/home/user/AAA/swarm/tests/__init__.py"
      provides: "Tests package initialization"
  key_links:
    - from: "task_queue.py"
      to: "/tmp/ai_swarm/"
      via: "os.path.join(base_dir, 'tasks.json')"
      pattern: "base_dir.*tmp.*ai_swarm"
    - from: "worker_smart.py"
      to: "/tmp/ai_swarm/"
      via: "os.path.join(self.base_dir, 'status.log')"
      pattern: "base_dir.*tmp.*ai_swarm"
    - from: "tests/*"
      to: "swarm/*"
      via: "import from swarm package"
      pattern: "from swarm"
---

<objective>
Restructure Phase 2 code into MVP directory layout, configure paths to use /tmp/ai_swarm/, and verify tests pass.

Purpose: Establish clean project structure for AI Swarm MVP with proper package layout and path configuration.

Output:
- swarm/ package with __init__.py and core modules (config.py, task_queue.py, worker_smart.py)
- scripts/ directory for startup scripts
- .env.example with required environment variables
- Updated path references to use /tmp/ai_swarm/
</objective>

<execution_context>
@/home/user/.claude/agents/gsd-planner.md
</execution_context>

<context>
@/home/user/AAA/swarm/.planning/phases/01-project-initialization/*-CONTEXT.md

# Current codebase (Phase 2):
- /home/user/AAA/swarm/config.py - Configuration module (API key, models, pricing)
- /home/user/AAA/swarm/task_queue.py - Task queue manager (uses ~/group/ai_swarm/)
- /home/user/AAA/swarm/worker_smart.py - Smart worker node (uses ~/group/ai_swarm/)
- /home/user/AAA/swarm/tests/ - Test suite (pytest based)

# Paths to update:
- task_queue.py:30 -> change ~/group/ai_swarm/ to /tmp/ai_swarm/
- worker_smart.py:41 -> change ~/group/ai_swarm/ to /tmp/ai_swarm/

# Target directory structure:
swarm/
  __init__.py
  config.py
  task_queue.py
  worker_smart.py
scripts/
  __init__.py
tests/
  __init__.py
  conftest.py (update imports)
.env.example
README.md (already exists)
</context>

<tasks>

<task type="auto">
  <name>Create swarm package directory structure</name>
  <files>
    /home/user/AAA/swarm/swarm/__init__.py
    /home/user/AAA/swarm/swarm/config.py
    /home/user/AAA/swarm/swarm/task_queue.py
    /home/user/AAA/swarm/swarm/worker_smart.py
    /home/user/AAA/swarm/scripts/__init__.py
  </files>
  <action>
    Create directories and copy files:
    1. Create /home/user/AAA/swarm/swarm/ directory
    2. Copy /home/user/AAA/swarm/config.py -> /home/user/AAA/swarm/swarm/config.py
    3. Copy /home/user/AAA/swarm/task_queue.py -> /home/user/AAA/swarm/swarm/task_queue.py
    4. Copy /home/user/AAA/swarm/worker_smart.py -> /home/user/AAA/swarm/swarm/worker_smart.py
    5. Create /home/user/AAA/swarm/scripts/ directory
    6. Create /home/user/AAA/swarm/swarm/__init__.py with version and imports
    7. Create /home/user/AAA/swarm/scripts/__init__.py (empty)

    Update imports in task_queue.py and worker_smart.py:
    - Change `import config` to `from swarm import config`
    - Change `import task_queue` to `from swarm import task_queue`
  </action>
  <verify>
    ls -la /home/user/AAA/swarm/swarm/ && ls -la /home/user/AAA/swarm/scripts/
    grep -r "from swarm import" /home/user/AAA/swarm/swarm/
  </verify>
  <done>
    swarm/ package has __init__.py, config.py, task_queue.py, worker_smart.py
    scripts/ directory exists
    Internal imports use "from swarm import" pattern
  </done>
</task>

<task type="auto">
  <name>Update paths with auto-create and env-override rules</name>
  <files>
    /home/user/AAA/swarm/swarm/task_queue.py
    /home/user/AAA/swarm/swarm/worker_smart.py
  </files>
  <action>
    **CRITICAL CONSTRAINTS (must follow):**

    1. **API Key only from env vars** - NO dotenv loading, NO .env auto-load
    2. **Auto-create /tmp/ai_swarm** - Use os.makedirs(base_dir, exist_ok=True)
    3. **AI_SWARM_DIR override** - Default /tmp/ai_swarm, use os.environ.get('AI_SWARM_DIR', '/tmp/ai_swarm/')
    4. **Use os.path.join** - Never concatenate with trailing slash: use os.path.join(base_dir, 'tasks.json')

    **Changes in task_queue.py:**
    - Line 30: Change to `base_dir = os.environ.get('AI_SWARM_DIR', '/tmp/ai_swarm/')`
    - Add: `os.makedirs(base_dir, exist_ok=True)` before any file operations
    - Change file paths to use `os.path.join(base_dir, 'tasks.json')`, `os.path.join(base_dir, 'locks/')`, etc.

    **Changes in worker_smart.py:**
    - Line 40-41: Change to `self.base_dir = os.environ.get('AI_SWARM_DIR', '/tmp/ai_swarm/')`
    - Add: `os.makedirs(self.base_dir, exist_ok=True)` in __init__
    - Change file paths to use `os.path.join(self.base_dir, 'status.log')`, etc.

    **Verify no dotenv loading** - grep for 'dotenv', 'load_dotenv', '.env' - none should exist
  </action>
  <verify>
    grep -n "AI_SWARM_DIR\|/tmp/ai_swarm\|os.makedirs\|os.path.join" /home/user/AAA/swarm/swarm/task_queue.py
    grep -n "AI_SWARM_DIR\|/tmp/ai_swarm\|os.makedirs\|os.path.join" /home/user/AAA/swarm/swarm/worker_smart.py
    grep -E "dotenv|load_dotenv" /home/user/AAA/swarm/swarm/*.py || echo "No dotenv found - PASS"
  </verify>
  <done>
    task_queue.py and worker_smart.py:
    - Use AI_SWARM_DIR env var (default /tmp/ai_swarm/)
    - Auto-create directory with os.makedirs(exist_ok=True)
    - Use os.path.join for all path construction
    - No dotenv or .env loading
  </done>
</task>

<task type="auto">
  <name>Update tests with isolation fixture via env injection</name>
  <files>
    /home/user/AAA/swarm/tests/__init__.py
    /home/user/AAA/swarm/tests/conftest.py
    /home/user/AAA/swarm/tests/test_config.py
    /home/user/AAA/swarm/tests/test_task_queue.py
    /home/user/AAA/swarm/tests/test_worker_smart.py
    /home/user/AAA/swarm/tests/test_master_dispatcher.py
  </files>
  <action>
    **CRITICAL CONSTRAINT:** Tests must be repeatable with pytest -q (no pollution between runs)

    1. Create /home/user/AAA/swarm/tests/__init__.py

    2. Create /home/user/AAA/swarm/tests/conftest.py with:
       - A pytest fixture that sets AI_SWARM_DIR to a temp directory
       - Fixture uses monkeypatch to set os.environ['AI_SWARM_DIR']
       - Fixture creates temp dir via tempfile.mkdtemp()
       - Fixture cleanup removes temp dir after test
       - All tests use this fixture to ensure isolation

    Example conftest.py pattern:
    ```python
    import pytest
    import tempfile
    import shutil
    import os

    @pytest.fixture(autouse=True)
    def isolated_swarm_dir(monkeypatch):
        temp_dir = tempfile.mkdtemp(prefix='ai_swarm_test_')
        monkeypatch.setenv('AI_SWARM_DIR', temp_dir)
        os.makedirs(temp_dir, exist_ok=True)
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    ```

    3. Update all test files to import from swarm package:
       - test_config.py: `from swarm import config`
       - test_task_queue.py: `from swarm import task_queue, config`
       - test_worker_smart.py: `from swarm import worker_smart, task_queue, config`
       - test_master_dispatcher.py: Update all imports

    4. Ensure NO test loads .env file directly
  </action>
  <verify>
    grep -r "from swarm import" /home/user/AAA/swarm/tests/
    grep -r "monkeypatch.*AI_SWARM_DIR\|tempfile.*ai_swarm" /home/user/AAA/swarm/tests/conftest.py || echo "Fixture not found"
    # Run tests twice to verify isolation
    pytest -q /home/user/AAA/swarm/tests/ --tb=short 2>&1 | tail -5
    pytest -q /home/user/AAA/swarm/tests/ --tb=short 2>&1 | tail -5
  </verify>
  <done>
    conftest.py has isolated_swarm_dir fixture that:
    - Sets AI_SWARM_DIR to temp directory via monkeypatch
    - Cleans up after each test session
    All test files import from swarm package
    Tests pass and are repeatable (run twice, same result)
  </done>
</task>

<task type="auto">
  <name>Create .env.example template</name>
  <files>
    /home/user/AAA/swarm/.env.example
  </files>
  <action>
    Create /home/user/AAA/swarm/.env.example with required environment variables:

    ```
    # AI Swarm Configuration
    # Copy this file to .env and fill in your values

    # API Key (required for direct mode)
    ANTHROPIC_API_KEY=sk-ant-api03-xxx

    # Optional: Use ccswitch proxy instead of direct API
    # LLM_BASE_URL=https://your-proxy-url

    # Swarm data directory (default: /tmp/ai_swarm/)
    # AI_SWARM_DIR=/path/to/your/data/directory
    ```

    Include comments explaining each variable and where to get the API key.
  </action>
  <verify>
    cat /home/user/AAA/swarm/.env.example
  </verify>
  <done>
    .env.example exists with ANTHROPIC_API_KEY and AI_SWARM_DIR variables
  </done>
</task>

</tasks>

<verification>
1. Directory structure matches target layout:
   ls -la /home/user/AAA/swarm/swarm/ && ls -la /home/user/AAA/swarm/scripts/

2. All path references updated:
   grep -r "/tmp/ai_swarm" /home/user/AAA/swarm/swarm/

3. Tests pass:
   pytest -q /home/user/AAA/swarm/tests/

4. .env.example created:
   ls -la /home/user/AAA/swarm/.env.example
</verification>

<success_criteria>
- [ ] swarm/ package created with __init__.py, config.py, task_queue.py, worker_smart.py
- [ ] scripts/ directory created
- [ ] All path references updated to use /tmp/ai_swarm/ (with AI_SWARM_DIR override)
- [ ] Tests pass: pytest -q /home/user/AAA/swarm/tests/ returns 0
- [ ] .env.example created with required environment variables
</success_criteria>

<output>
After completion, create `.planning/phases/01-project-initialization/01-SUMMARY.md` with:
- Frontmatter: phase, plan, completed, timestamp, files_created, tests_run
- Summary of changes made
- Test results
- Any issues encountered
</output>
