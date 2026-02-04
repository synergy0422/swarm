---
phase: quick-test-mode
plan: "001"
type: execute
wave: 1
depends_on: []
files_modified: ["swarm/cli.py", "scripts/swarm_task_wrap.sh"]
autonomous: true
user_setup: []

must_haves:
  truths:
    - "`swarm task run --dry-run` shows command without executing"
    - "Dangerous commands (rm -rf, etc.) are flagged with warning"
    - "Test mode returns exit code 0 without side effects"
  artifacts:
    - path: "swarm/cli.py"
      provides: "dry-run flag parsing for cmd_task_run"
      min_lines: 10
    - path: "scripts/swarm_task_wrap.sh"
      provides: "--dry-run flag and dangerous command detection"
      min_lines: 30
  key_links:
    - from: "swarm/cli.py"
      to: "scripts/swarm_task_wrap.sh"
      via: "DRY_RUN=1 environment variable"
      pattern: "DRY_RUN"
---

<objective>
Add test mode and safe execution to `swarm task run`.

Purpose: Enable safe testing of task execution without side effects, and warn about dangerous commands.
Output: Modified cli.py and swarm_task_wrap.sh with dry-run and safety features.
</objective>

<execution_context>
@/home/user/projects/AAA/swarm/.planning/quick/001-test-mode-for-swarm-task/001-PLAN.md
</execution_context>

<context>
@/home/user/projects/AAA/swarm/swarm/cli.py (cmd_task_run at line 687)
@/home/user/projects/AAA/swarm/scripts/swarm_task_wrap.sh (cmd_run at line 143)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add --dry-run flag support to cmd_task_run in cli.py</name>
  <files>swarm/cli.py</files>
  <action>
    Modify cmd_task_run function (line 687-700) to:
    1. Accept --dry-run flag before positional args: check for '--dry-run' in args.command list
    2. When dry-run is set, set environment variable DRY_RUN=1 before calling swarm_task_wrap.sh
    3. Pass --dry-run to swarm_task_wrap.sh as a global option (before 'run')
    4. Print "[DRY-RUN]" prefix before showing what would be executed
    5. Return exit code 0 without executing the underlying script

    Example behavior:
    - `swarm task run --dry-run task-001 worker-0 echo hello`
    - Output: "[DRY-RUN] Would execute: echo hello"
    - Exit code: 0
  </action>
  <verify>
    grep -n "DRY_RUN" swarm/cli.py
    python3 -m swarm.cli task run --dry-run test-worker-0 echo hello
    Expected: "[DRY-RUN]" prefix in output, exit code 0
  </verify>
  <done>
    cli.py accepts --dry-run flag and sets DRY_RUN=1 environment variable
  </done>
</task>

<task type="auto">
  <name>Task 2: Implement --dry-run and dangerous command detection in swarm_task_wrap.sh</name>
  <files>scripts/swarm_task_wrap.sh</files>
  <action>
    Modify swarm_task_wrap.sh to:
    1. Add --dry-run global option parsing in main() function (around line 211)
       - Set DRY_RUN=1 when flag is present

    2. Add dangerous command detection function near top of script:
       - Define DANGEROUS_PATTERNS array: rm -rf, dd if=/dev, mkfs, shred, format, :(){:|:&}
       - Function is_command_safe() that checks if command contains any dangerous pattern
       - Function warn_dangerous() that logs warning for dangerous commands

    3. Modify cmd_run() function (line 143) to:
       - If DRY_RUN=1: print command that would be executed and exit 0
       - Before executing, call is_command_safe() to check for dangerous commands
       - If dangerous and not DRY_RUN: log warning and continue (don't block)
       - If DRY_RUN and dangerous: still show the command with warning

    4. Add --dry-run to usage() help text
  </action>
  <verify>
    grep -n "DANGEROUS\|DRY_RUN\|is_command_safe" scripts/swarm_task_wrap.sh
    DRY_RUN=1 scripts/swarm_task_wrap.sh run test-worker echo hello
    Expected: "[DRY-RUN]" or similar output, exit code 0
  </verify>
  <done>
    swarm_task_wrap.sh has --dry-run option and dangerous command detection
  </done>
</task>

</tasks>

<verification>
1. `swarm task run --dry-run task-001 worker-0 echo hello` shows "[DRY-RUN]" prefix, exits 0
2. `swarm task run --dry-run task-001 worker-0 rm -rf /` shows warning but exits 0
3. `swarm task run task-001 worker-0 echo hello` executes normally, exits with command's exit code
4. `swarm task run task-001 worker-0 rm -rf /tmp/test` logs warning but executes
</verification>

<success_criteria>
- `swarm task run --dry-run` works without side effects
- Dangerous commands are flagged with warning
- Exit codes are correct (0 for dry-run, command exit for real run)
- Existing functionality preserved (swarm task claim/done/fail unaffected)
</success_criteria>

<output>
After completion, create `.planning/quick/001-test-mode-for-swarm-task/001-SUMMARY.md`
</output>
