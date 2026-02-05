#!/usr/bin/env python3
"""
AI Swarm CLI - Unified Command Line Interface

Provides docker-compose-like interface for launching swarm clusters:
- swarm init: Initialize environment and dependencies
- swarm up: Launch tmux session with master + N workers
- swarm master: Launch only master process
- swarm worker: Launch single worker
- swarm status: View tmux session and agent status
- swarm down: Terminate swarm tmux session
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


# Default configuration
DEFAULT_CLUSTER_ID = "default"
DEFAULT_WORKERS = 3
DEFAULT_AI_SWARM_DIR = "/tmp/ai_swarm"


def check_tmux_installed():
    """Check if tmux binary is available"""
    return shutil.which('tmux') is not None


def check_libtmux_available():
    """Check if libtmux is installed"""
    try:
        import libtmux
        return True
    except ImportError:
        return False


def preflight_check():
    """
    Perform preflight checks for all commands.

    Returns:
        bool: True if all critical checks pass
    """
    errors = []
    warnings = []

    # Check tmux binary
    if not check_tmux_installed():
        errors.append("tmux binary not found. Install tmux: apt install tmux or brew install tmux")

    # Check libtmux
    if not check_libtmux_available():
        errors.append("libtmux not installed. Install: pip install libtmux")

    # Check AI_SWARM_DIR
    ai_swarm_dir = os.environ.get('AI_SWARM_DIR', DEFAULT_AI_SWARM_DIR)
    if not os.path.exists(ai_swarm_dir):
        try:
            os.makedirs(ai_swarm_dir, exist_ok=True)
            warnings.append(f"Created AI_SWARM_DIR: {ai_swarm_dir}")
        except Exception as e:
            errors.append(f"Cannot create AI_SWARM_DIR {ai_swarm_dir}: {e}")

    # Check API key (warning only)
    api_key = os.environ.get('ANTHROPIC_API_KEY') or os.environ.get('OPENAI_API_KEY')
    llm_base_url = os.environ.get('LLM_BASE_URL')

    if not api_key and not llm_base_url:
        warnings.append("ANTHROPIC_API_KEY or LLM_BASE_URL not set (workers will fail)")

    # Print results
    if warnings:
        for warning in warnings:
            print(f"[WARNING] {warning}")

    if errors:
        for error in errors:
            print(f"[ERROR] {error}", file=sys.stderr)
        return False

    return True


def llm_env_ok() -> bool:
    """
    Check if LLM environment is configured for workers.

    Returns:
        bool: True if ANTHROPIC_API_KEY or LLM_BASE_URL is set.
    """
    api_key = os.environ.get('ANTHROPIC_API_KEY') or os.environ.get('OPENAI_API_KEY')
    llm_base_url = os.environ.get('LLM_BASE_URL')
    return bool(api_key or llm_base_url)


def cmd_init(args):
    """
    Initialize swarm environment.

    Checks dependencies and creates directory structure.
    """
    print("[SWARM] Initializing swarm environment...")

    # Check libtmux
    if not check_libtmux_available():
        print("[ERROR] libtmux not installed", file=sys.stderr)
        print("Install: pip install libtmux", file=sys.stderr)
        return 1

    # Check tmux binary
    if not check_tmux_installed():
        print("[ERROR] tmux binary not found", file=sys.stderr)
        print("Install: apt install tmux or brew install tmux", file=sys.stderr)
        return 1

    # Get AI_SWARM_DIR
    ai_swarm_dir = os.environ.get('AI_SWARM_DIR', DEFAULT_AI_SWARM_DIR)

    # Create directory structure
    print(f"[SWARM] Creating directory structure: {ai_swarm_dir}")
    try:
        os.makedirs(ai_swarm_dir, exist_ok=True)
        os.makedirs(os.path.join(ai_swarm_dir, 'status'), exist_ok=True)
        os.makedirs(os.path.join(ai_swarm_dir, 'locks'), exist_ok=True)
        os.makedirs(os.path.join(ai_swarm_dir, 'results'), exist_ok=True)
        os.makedirs(os.path.join(ai_swarm_dir, 'instructions'), exist_ok=True)
    except Exception as e:
        print(f"[ERROR] Failed to create directories: {e}", file=sys.stderr)
        return 1

    # Print environment checklist
    print("\n[SWARM] Environment Checklist:")
    print(f"  AI_SWARM_DIR: {ai_swarm_dir}")

    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if api_key:
        print(f"  ANTHROPIC_API_KEY: {'*' * 20}{api_key[-4:]}")
    else:
        print("  ANTHROPIC_API_KEY: (not set)")

    llm_base_url = os.environ.get('LLM_BASE_URL')
    if llm_base_url:
        print(f"  LLM_BASE_URL: {llm_base_url}")
    else:
        print("  LLM_BASE_URL: (not set)")
        print("\n[SWARM] Default cc-switch example:")
        print("  export LLM_BASE_URL=\"http://127.0.0.1:15721/v1/messages\"")
        print("  export ANTHROPIC_API_KEY=\"dummy\"")

    print("\n[SWARM] Swarm initialized successfully!")
    print(f"[SWARM] Directory: {ai_swarm_dir}")
    return 0


def cmd_master(args):
    """
    Launch master process.

    Directly instantiates Master class to avoid argparse conflicts.
    """
    try:
        from swarm.master import Master
        from swarm.tmux_collaboration import TmuxCollaboration

        print(f"[SWARM] Starting master for cluster: {args.cluster_id}")
        print("[SWARM] Press Ctrl+C to stop")

        # Create TmuxCollaboration if tmux is available
        tmux_collaboration = None
        try:
            tmux_collaboration = TmuxCollaboration()
            # Verify tmux is actually working by listing windows
            tmux_collaboration.list_windows(f"swarm-{args.cluster_id}")
        except Exception:
            # tmux not available, continue without it
            pass

        master = Master(
            cluster_id=args.cluster_id,
            tmux_collaboration=tmux_collaboration
        )
        master.run()
        return 0
    except KeyboardInterrupt:
        print("\n[SWARM] Master interrupted by user")
        return 0
    except Exception as e:
        print(f"[ERROR] Master failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def cmd_worker(args):
    """
    Launch single worker process.

    Creates SmartWorker instance and calls run().
    """
    try:
        if not llm_env_ok():
            print("[ERROR] No LLM config found. Set LLM_BASE_URL (cc-switch proxy) or ANTHROPIC_API_KEY.", file=sys.stderr)
            print("        Example for cc-switch:", file=sys.stderr)
            print("        export LLM_BASE_URL=\"http://127.0.0.1:15721/v1/messages\"", file=sys.stderr)
            print("        export ANTHROPIC_API_KEY=\"dummy\"", file=sys.stderr)
            return 1
        from swarm.worker_smart import SmartWorker
        worker_name = f"worker-{args.id}"
        print(f"[SWARM] Starting worker: {worker_name}")
        print("[SWARM] Press Ctrl+C to stop")
        worker = SmartWorker(name=worker_name)
        return worker.run()
    except KeyboardInterrupt:
        print(f"\n[SWARM] Worker {args.id} interrupted by user")
        return 0
    except Exception as e:
        print(f"[ERROR] Worker failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def get_session(cluster_id):
    """
    Get tmux session by cluster ID.

    Args:
        cluster_id: Cluster identifier

    Returns:
        libtmux Session or None
    """
    try:
        import libtmux
        server = libtmux.Server()
        session_name = f"swarm-{cluster_id}"
        # Find session by name using attribute access
        for s in server.sessions:
            if s.session_name == session_name:
                return s
        return None
    except ImportError:
        return None
    except Exception:
        return None


def tmux_has_session(cluster_id):
    """
    Check if a tmux session exists (without libtmux).
    """
    import subprocess
    session_name = f"swarm-{cluster_id}"
    result = subprocess.run(
        ['tmux', 'has-session', '-t', session_name],
        capture_output=True
    )
    return result.returncode == 0


def cmd_up(args):
    """
    Launch tmux session with master + N workers.

    Uses subprocess to call tmux directly, avoiding libtmux API issues.
    """
    import subprocess

    cluster_id = args.cluster_id
    workers = args.workers
    session_name = f"swarm-{cluster_id}"

    # Preflight checks
    if not check_tmux_installed():
        print("[ERROR] tmux not installed", file=sys.stderr)
        return 1
    if not llm_env_ok():
        print("[ERROR] No LLM config found. Set LLM_BASE_URL (cc-switch proxy) or ANTHROPIC_API_KEY.", file=sys.stderr)
        print("        Example for cc-switch:", file=sys.stderr)
        print("        export LLM_BASE_URL=\"http://127.0.0.1:15721/v1/messages\"", file=sys.stderr)
        print("        export ANTHROPIC_API_KEY=\"dummy\"", file=sys.stderr)
        return 1

    # Check if session already exists
    if tmux_has_session(cluster_id):
        print(f"[ERROR] Swarm session already exists: {session_name}", file=sys.stderr)
        print(f"[ERROR] Run 'swarm down --cluster-id {cluster_id}' first", file=sys.stderr)
        return 1

    # Ensure directory exists
    ai_swarm_dir = os.environ.get('AI_SWARM_DIR', '/tmp/ai_swarm')
    os.makedirs(ai_swarm_dir, exist_ok=True)

    print(f"[SWARM] Creating tmux session: {session_name}")

    # Prepare env without TMUX variable (causes issues with detached sessions)
    env = os.environ.copy()
    env.pop('TMUX', None)
    env.pop('TMUX_PANE', None)

    try:
        # Inject environment variables BEFORE creating windows (before master starts)
        # Using tmux set-environment -g (global session variable)
        # This must be done BEFORE new-session, so we set via environment to subprocess
        llm_base_url = os.environ.get('LLM_BASE_URL', '')
        api_key = os.environ.get('ANTHROPIC_API_KEY', '')

        # Pass environment variables to subprocess env (will be inherited by tmux session)
        env['AI_SWARM_DIR'] = ai_swarm_dir
        if llm_base_url:
            env['LLM_BASE_URL'] = llm_base_url
        if api_key:
            env['ANTHROPIC_API_KEY'] = api_key

        # Create master window with master command
        master_cmd = f'python3 -m swarm.cli --cluster-id {cluster_id} master'
        subprocess.run([
            'tmux', 'new-session', '-d', '-s', session_name,
            '-n', 'master', '-x', '80', '-y', '24',
            master_cmd
        ], check=True, env=env)

        # Also set environment in tmux session for any new windows created
        # This ensures child processes via tmux also see these vars
        subprocess.run([
            'tmux', 'set-environment', '-t', session_name,
            'AI_SWARM_DIR', ai_swarm_dir
        ], check=False)

        if llm_base_url:
            subprocess.run([
                'tmux', 'set-environment', '-t', session_name,
                'LLM_BASE_URL', llm_base_url
            ], check=False)

        if api_key:
            subprocess.run([
                'tmux', 'set-environment', '-t', session_name,
                'ANTHROPIC_API_KEY', api_key
            ], check=False)

        # Create worker windows
        for i in range(workers):
            worker_cmd = f'python3 -m swarm.cli --cluster-id {cluster_id} worker --id {i}'
            subprocess.run([
                'tmux', 'new-window', '-t', session_name,
                '-n', f'worker-{i}', worker_cmd
            ], check=True, env=env)

        print(f"\n[SWARM] Swarm session created: {session_name}")
        print(f"[SWARM] Master + {workers} workers launched")
        print(f"\n[SWARM] Attach to session:")
        print(f"[SWARM]   tmux attach -t {session_name}")
        print(f"\n[SWARM] Check status:")
        print(f"[SWARM]   python3 -m swarm.cli --cluster-id {cluster_id} status")
        print(f"\n[SWARM] Stop swarm:")
        print(f"[SWARM]   python3 -m swarm.cli --cluster-id {cluster_id} down")

        return 0

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to create tmux session: {e}", file=sys.stderr)
        print("[SWARM] Attempting cleanup...")
        cmd_down(args)
        return 1
    except Exception as e:
        print(f"[ERROR] Failed to create session: {e}", file=sys.stderr)
        print("[SWARM] Attempting cleanup...")
        cmd_down(args)
        return 1
        return 1


def parse_status_log(ai_swarm_dir, lines=10):
    """
    Parse last N lines from status.log.

    Args:
        ai_swarm_dir: Base directory
        lines: Number of lines to read

    Returns:
        dict: Mapping of worker_id -> latest status
    """
    import json
    from collections import defaultdict

    status_log = os.path.join(ai_swarm_dir, 'status.log')
    worker_status = {}

    if not os.path.exists(status_log):
        return worker_status

    try:
        all_lines = []
        with open(status_log, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entry = json.loads(line)
                        all_lines.append(entry)
                    except json.JSONDecodeError:
                        continue

        # Get last N lines and extract latest status per worker
        for entry in all_lines[-lines:]:
            worker_id = entry.get('worker_id')
            if worker_id:
                worker_status[worker_id] = entry

    except (IOError, OSError):
        pass

    return worker_status


def format_pane_output(pane_contents: dict) -> str:
    """
    Format pane output for display in swarm status.

    Args:
        pane_contents: Dictionary mapping window names to their pane content.

    Returns:
        Formatted string with pane snapshots for master, worker-0, worker-1, worker-2.
    """
    REQUIRED_WINDOWS = ["master", "worker-0", "worker-1", "worker-2"]
    MAX_LINES = 20

    output_parts = []

    for window_name in REQUIRED_WINDOWS:
        content = pane_contents.get(window_name, "")

        # Determine status icon
        content_lower = content.lower()
        if "error" in content_lower or "failed" in content_lower:
            status = "[ERROR]"
        elif "done" in content_lower or "complete" in content_lower:
            status = "[DONE]"
        else:
            status = "[ ]"

        # Format this window's output
        output_parts.append(f"=== {window_name} {status} ===")

        if content:
            lines = content.split('\n')
            last_lines = lines[-MAX_LINES:] if len(lines) > MAX_LINES else lines
            output_parts.append('\n'.join(last_lines))
        else:
            output_parts.append("(missing)")

        output_parts.append("")  # Empty line between windows

    return '\n'.join(output_parts)


def cmd_status(args):
    """
    Display swarm status.

    Shows tmux session info and worker status from status.log.
    """
    ai_swarm_dir = os.environ.get('AI_SWARM_DIR', DEFAULT_AI_SWARM_DIR)
    session_name = f"swarm-{args.cluster_id}"

    # Check tmux session
    session = get_session(args.cluster_id)
    if not session:
        if not tmux_has_session(args.cluster_id):
            print(f"[SWARM] No swarm session running: {session_name}")
            print(f"[SWARM] Run 'swarm up --cluster-id {args.cluster_id}' to start")
            return 0
        print(f"[SWARM] Session: {session_name}")
        print("[SWARM] TMUX Windows: (libtmux not available)")
    else:
        print(f"[SWARM] Session: {session_name}")

        # List windows/panes
        print(f"\n[SWARM] TMUX Windows:")
        for window in session.windows:
            print(f"  - {window.name}")

    # Parse status.log
    worker_status = parse_status_log(ai_swarm_dir, lines=20)

    if worker_status:
        print(f"\n[SWARM] Agent Status (from status.log):")
        print(f"  {'Agent':<15} {'State':<10} {'Message'}")
        print(f"  {'-'*15} {'-'*10} {'-'*40}")

        for worker_id in sorted(worker_status.keys()):
            status = worker_status[worker_id]
            state = status.get('state', 'UNKNOWN')
            message = status.get('message', '')[:40]
            print(f"  {worker_id:<15} {state:<10} {message}")
    else:
        print(f"\n[SWARM] No agent status available yet")

    # Check active locks
    locks_dir = os.path.join(ai_swarm_dir, 'locks')
    if os.path.exists(locks_dir):
        lock_files = [f for f in os.listdir(locks_dir) if f.endswith('.lock')]
        if lock_files:
            print(f"\n[SWARM] Active Locks: {len(lock_files)}")
            for lock_file in sorted(lock_files)[:5]:  # Show first 5
                print(f"  - {lock_file}")

    # Handle --panes flag for window content snapshots
    if getattr(args, 'panes', False):
        if not check_tmux_installed():
            print("\n[WARNING] tmux not available, skipping pane display")
        else:
            try:
                from swarm.tmux_collaboration import TmuxCollaboration
                tmux_collaboration = TmuxCollaboration()
                pane_contents = tmux_collaboration.capture_all_windows(f"swarm-{args.cluster_id}")
                if pane_contents:
                    pane_output = format_pane_output(pane_contents)
                    print(f"\n{pane_output}")
                # If pane_contents is empty, session doesn't exist - skip silently
            except Exception:
                # Session doesn't exist or other error - skip panes silently
                pass

    return 0


def cmd_down(args):
    """
    Terminate swarm session.

    Kills tmux session if it exists.
    """
    session_name = f"swarm-{args.cluster_id}"

    try:
        # Kill session (libtmux preferred, tmux fallback)
        session = get_session(args.cluster_id)
        if session:
            session.kill()
            print(f"[SWARM] Swarm session stopped: {session_name}")
            return 0
        if tmux_has_session(args.cluster_id):
            import subprocess
            subprocess.run(
                ['tmux', 'kill-session', '-t', session_name],
                check=False
            )
            print(f"[SWARM] Swarm session stopped: {session_name}")
            return 0
        print(f"[SWARM] No swarm session running: {session_name}")
        return 0
    except Exception as e:
        print(f"[ERROR] Failed to stop session: {e}", file=sys.stderr)
        return 1


def cmd_task(args):
    """
    Dispatch to task subcommand handlers.
    args.task_command: the subcommand (claim, done, fail, run)
    args.task_args: remaining arguments for the subcommand
    """
    import argparse as _argparse

    if args.task_command is None:
        # No subcommand specified, show task help with subcommands
        print("usage: swarm task <command> [<args>]")
        print("")
        print("Task management commands:")
        print("  add \"<prompt>\"                  Add task via FIFO (or - for stdin)")
        print("  claim <task_id> <worker> [lock_key]  Claim a task")
        print("  done <task_id> <worker> [lock_key]   Mark task as done")
        print("  fail <task_id> <worker> <reason> [lock_key]  Mark task as failed")
        print("  run <task_id> <worker> <command...>  Run task command wrapper")
        print("")
        print("Use 'swarm task <command> --help' for more info on a command.")
        return 0

    # Parse task_args based on subcommand
    task_cmd = args.task_command
    task_args = args.task_args if args.task_args else []

    if task_cmd == 'claim':
        # claim <task_id> <worker> [lock_key]
        # Check for --help before parsing
        if '--help' in task_args or '-h' in task_args:
            print("usage: swarm task claim <task_id> <worker> [lock_key]")
            print("")
            print("Claim a task:")
            print("  <task_id>   Task ID to claim")
            print("  <worker>   Worker name claiming the task")
            print("  [lock_key] Optional lock key (defaults to task_id)")
            return 0
        parser = _argparse.ArgumentParser(prog=f'swarm task {task_cmd}', parents=[], add_help=False)
        parser.add_argument('task_id', help='Task ID to claim')
        parser.add_argument('worker', help='Worker name claiming the task')
        parser.add_argument('lock_key', nargs='?', default=None, help='Optional lock key')
        try:
            parsed = parser.parse_args(task_args)
        except SystemExit:
            return 1
        return cmd_task_claim(parsed)

    elif task_cmd == 'done':
        # done <task_id> <worker> [lock_key]
        # Check for --help before parsing
        if '--help' in task_args or '-h' in task_args:
            print("usage: swarm task done <task_id> <worker> [lock_key]")
            print("")
            print("Mark task as done:")
            print("  <task_id>   Task ID to complete")
            print("  <worker>   Worker completing the task")
            print("  [lock_key] Optional lock key (defaults to task_id)")
            return 0
        parser = _argparse.ArgumentParser(prog=f'swarm task {task_cmd}', parents=[], add_help=False)
        parser.add_argument('task_id', help='Task ID to complete')
        parser.add_argument('worker', help='Worker completing the task')
        parser.add_argument('lock_key', nargs='?', default=None, help='Optional lock key')
        try:
            parsed = parser.parse_args(task_args)
        except SystemExit:
            return 1
        return cmd_task_done(parsed)

    elif task_cmd == 'fail':
        # fail <task_id> <worker> <reason> [lock_key]
        # Check for --help before parsing
        if '--help' in task_args or '-h' in task_args:
            print("usage: swarm task fail <task_id> <worker> <reason> [lock_key]")
            print("")
            print("Mark task as failed:")
            print("  <task_id>   Task ID that failed")
            print("  <worker>   Worker reporting failure")
            print("  <reason>   Failure reason")
            print("  [lock_key] Optional lock key (defaults to task_id)")
            return 0
        parser = _argparse.ArgumentParser(prog=f'swarm task {task_cmd}', parents=[], add_help=False)
        parser.add_argument('task_id', help='Task ID that failed')
        parser.add_argument('worker', help='Worker reporting failure')
        parser.add_argument('reason', help='Failure reason')
        parser.add_argument('lock_key', nargs='?', default=None, help='Optional lock key')
        try:
            parsed = parser.parse_args(task_args)
        except SystemExit:
            return 1
        return cmd_task_fail(parsed)

    elif task_cmd == 'run':
        # run <task_id> <worker> <command...>
        # Check for --help before parsing
        if '--help' in task_args or '-h' in task_args:
            print("usage: swarm task run <task_id> <worker> <command...>")
            print("")
            print("Run task command wrapper:")
            print("  <task_id>   Task ID")
            print("  <worker>   Worker name")
            print("  <command...>  Command to execute")
            return 0

        # Manually parse task_id, worker, and command (to handle -rf, --flag etc.)
        if len(task_args) < 3:
            print("usage: swarm task run <task_id> <worker> <command...>", file=sys.stderr)
            print("error: the following arguments are required: command", file=sys.stderr)
            return 1

        # Extract task_id (first arg) and worker (second arg)
        task_id = task_args[0]
        worker = task_args[1]
        command = task_args[2:]  # All remaining args are the command

        # Create a simple namespace-like object
        class Args:
            pass
        parsed = Args()
        parsed.task_id = task_id
        parsed.worker = worker
        parsed.command = command

        # Preserve dry_run flag from main() args
        parsed.dry_run = getattr(args, 'dry_run', False)
        return cmd_task_run(parsed)

    elif task_cmd == 'add':
        # add "<prompt>"  or  add -
        # Check for --help before parsing
        if '--help' in task_args or '-h' in task_args:
            print("usage: swarm task add \"<prompt>\"")
            print("       swarm task add -")
            print("")
            print("Add task via FIFO:")
            print("  \"<prompt>\"   Task prompt (quoted string)")
            print("  -            Read prompt from stdin")
            print("")
            print("Examples:")
            print("  swarm task add \"Review PR #123\"")
            print("  echo \"Fix bug\" | swarm task add -")
            return 0

        # Parse: add takes optional prompt or stdin flag
        parser = _argparse.ArgumentParser(prog=f'swarm task {task_cmd}', parents=[], add_help=False)
        parser.add_argument('prompt', nargs='?', default=None, help='Task prompt')
        parser.add_argument('stdin_flag', nargs='?', const='-', default=None, help='Read from stdin')
        try:
            parsed = parser.parse_args(task_args)
        except SystemExit:
            return 1
        return cmd_task_add(parsed)

    else:
        print(f"[ERROR] Unknown task command: {task_cmd}", file=sys.stderr)
        return 1


def _get_script_path(script_name):
    """
    Get absolute path to script in scripts/ directory.
    Works regardless of current working directory.
    """
    script_dir = os.path.join(os.path.dirname(__file__), '..', 'scripts')
    script_dir = os.path.abspath(script_dir)
    return os.path.join(script_dir, script_name)


def cmd_task_claim(args):
    """
    Call swarm_tasks_bridge.sh claim with task_id, worker, [lock_key].
    Exit codes: 0=success, 2=lock occupied, 1=other error
    """
    cmd = [_get_script_path('swarm_tasks_bridge.sh'), 'claim', args.task_id, args.worker]
    if args.lock_key:
        cmd.append(args.lock_key)

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip(), file=sys.stderr)

    return result.returncode


def cmd_task_done(args):
    """
    Call swarm_tasks_bridge.sh done with task_id, worker, [lock_key].
    Exit codes: 0=success, 1=failure
    """
    cmd = [_get_script_path('swarm_tasks_bridge.sh'), 'done', args.task_id, args.worker]
    if args.lock_key:
        cmd.append(args.lock_key)

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip(), file=sys.stderr)

    return result.returncode


def cmd_task_fail(args):
    """
    Call swarm_tasks_bridge.sh fail with task_id, worker, reason, [lock_key].
    Exit codes: 0=success, 1=failure
    """
    cmd = [_get_script_path('swarm_tasks_bridge.sh'), 'fail', args.task_id, args.worker, args.reason]
    if args.lock_key:
        cmd.append(args.lock_key)

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip(), file=sys.stderr)

    return result.returncode


def cmd_task_add(args):
    """
    Write task prompt to FIFO for master to pick up.

    Exit codes: 0=success, 1=error (FIFO not found, no reader, etc.)

    Usage:
      swarm task add "prompt text"      # From argument
      swarm task add -                   # From stdin
      echo "text" | swarm task add -    # Piped stdin
    """
    from swarm.fifo_input import get_fifo_path, write_to_fifo_nonblocking

    fifo_path = get_fifo_path()

    # Determine prompt source
    prompt = None

    # Check for stdin flag '-'
    if hasattr(args, 'stdin_flag') and args.stdin_flag:
        prompt = sys.stdin.read().strip()
    elif args.prompt:
        prompt = args.prompt
    else:
        # No arg, try reading from stdin (non-blocking check)
        if not sys.stdin.isatty():
            prompt = sys.stdin.read().strip()

    if not prompt:
        print("[ERROR] No prompt provided", file=sys.stderr)
        print("[ERROR] Usage: swarm task add \"<prompt>\" OR echo \"<prompt>\" | swarm task add -", file=sys.stderr)
        return 1

    # Write to FIFO with non-blocking (won't hang if no reader)
    try:
        success = write_to_fifo_nonblocking(fifo_path, prompt)
        if not success:
            print(f"[ERROR] No reader on FIFO (is master running with AI_SWARM_INTERACTIVE=1?)", file=sys.stderr)
            return 1
    except FileNotFoundError:
        print(f"[ERROR] FIFO not found: {fifo_path}", file=sys.stderr)
        print("[ERROR] Is master running with AI_SWARM_INTERACTIVE=1?", file=sys.stderr)
        return 1
    except BrokenPipeError:
        print("[ERROR] FIFO write failed (reader closed?)", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[ERROR] FIFO write failed: {e}", file=sys.stderr)
        return 1

    print(f"[OK] Task written to FIFO: {prompt[:50]}...")
    return 0


def cmd_task_run(args):
    """
    Call swarm_task_wrap.sh run with task_id, worker, command....
    Exit codes: command exit code

    Supports --dry-run flag (passed via command args):
    - When --dry-run is present, prints command without executing
    """
    # If dry_run flag was passed (extracted from argv by main())
    dry_run = getattr(args, 'dry_run', False)

    if dry_run:
        cmd_str = ' '.join(args.command)

        # Check for dangerous commands (mirrors wrap.sh detection)
        dangerous_patterns = [
            ('rm -rf', 'rm -rf'),
            ('rm -rf /', 'rm -rf /'),
            ('dd if=/dev', 'dd if=/dev'),
            ('mkfs', 'mkfs'),
            ('shred', 'shred'),
            ('format', 'format'),
            (':(){:|:&}', ':(){:|:&}'),
            ('>$', '>$'),
            ('dd of=/dev', 'dd of=/dev'),
        ]

        # Warn about dangerous commands (case-insensitive matching)
        cmd_lower = cmd_str.lower()
        for pattern, display in dangerous_patterns:
            if pattern.lower() in cmd_lower:
                print(f"[WARNING] DANGEROUS COMMAND DETECTED: contains '{display}'", file=sys.stderr)
                print(f"[WARNING] Command: {cmd_str}", file=sys.stderr)
                print(f"[WARNING] This command may cause data loss or system damage!", file=sys.stderr)
                break

        print(f"[DRY-RUN] Would execute: {cmd_str}")
        print(f"[DRY-RUN] Task: {args.task_id} on {args.worker}")
        return 0

    # Normal execution
    cmd = [_get_script_path('swarm_task_wrap.sh'), 'run', args.task_id, args.worker] + args.command

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip(), file=sys.stderr)

    return result.returncode


def main():
    """Main CLI entry point"""
    # Pre-parse --cluster-id to allow it before subcommand
    cluster_id = DEFAULT_CLUSTER_ID
    dry_run = False
    argv_copy = sys.argv[1:]

    # Look for --cluster-id and extract its value
    i = 0
    while i < len(argv_copy):
        if argv_copy[i].startswith('--cluster-id='):
            cluster_id = argv_copy[i].split('=', 1)[1]
            argv_copy = argv_copy[:i] + argv_copy[i + 1:]
            continue
        if argv_copy[i] == '--cluster-id':
            if i + 1 < len(argv_copy):
                cluster_id = argv_copy[i + 1]
                # Remove --cluster-id and its value from argv
                argv_copy = argv_copy[:i] + argv_copy[i + 2:]
            else:
                print("[ERROR] --cluster-id requires a value", file=sys.stderr)
                return 1
        elif argv_copy[i] == '--dry-run':
            dry_run = True
            argv_copy = argv_copy[:i] + argv_copy[i + 1:]
            continue  # Don't increment i, just continue with same index
        else:
            i += 1

    # Parent parser for common arguments (shared across subcommands)
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        '--cluster-id',
        default=cluster_id,
        help=f'Cluster identifier (default: {DEFAULT_CLUSTER_ID})'
    )

    parser = argparse.ArgumentParser(
        description='AI Swarm - Multi-Agent Task Processing System',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # init command (no --cluster-id - creates the environment, cluster not yet relevant)
    subparsers.add_parser('init', help='Initialize swarm environment')

    # up command
    up_parser = subparsers.add_parser('up', parents=[parent_parser], help='Launch tmux session with master + workers')
    up_parser.add_argument(
        '--workers',
        type=int,
        default=DEFAULT_WORKERS,
        help=f'Number of worker processes (default: {DEFAULT_WORKERS})'
    )

    # master command
    subparsers.add_parser('master', parents=[parent_parser], help='Launch master process')

    # worker command
    worker_parser = subparsers.add_parser('worker', parents=[parent_parser], help='Launch single worker')
    worker_parser.add_argument(
        '--id',
        type=int,
        required=True,
        help='Worker ID (e.g., 1 for worker-1)'
    )

    # status command
    status_parser = subparsers.add_parser('status', parents=[parent_parser], help='View swarm status')
    status_parser.add_argument(
        '--panes',
        action='store_true',
        default=False,
        help='Display tmux window pane snapshots'
    )

    # down command
    subparsers.add_parser('down', parents=[parent_parser], help='Terminate swarm session')

    # task command - use a simpler parser for the main subcommand
    task_parser = subparsers.add_parser('task', parents=[parent_parser], help='Task management commands (add, claim, done, fail, run)')
    task_parser.add_argument('task_command', nargs='?', default=None, help='Task subcommand (add, claim, done, fail, run)')
    task_parser.add_argument('task_args', nargs=argparse.REMAINDER, help='Arguments for task subcommand')

    # Override task_parser's _get_formatter to show custom help
    def _custom_help(self):
        print("usage: swarm task <command> [<args>]")
        print("")
        print("Task management commands:")
        print("  add \"<prompt>\"                  Add task via FIFO (or - for stdin)")
        print("  claim <task_id> <worker> [lock_key]  Claim a task")
        print("  done <task_id> <worker> [lock_key]   Mark task as done")
        print("  fail <task_id> <worker> <reason> [lock_key]  Mark task as failed")
        print("  run <task_id> <worker> <command...>  Run task command wrapper")
        print("")
        print("Use 'swarm task <command> --help' for more info on a command.")
        sys.exit(0)

    task_parser.print_help = lambda: _custom_help(task_parser)

    # Parse args with modified argv (--cluster-id already extracted)
    args = parser.parse_args(argv_copy)

    # Add dry_run flag to args object
    args.dry_run = dry_run

    # Route to command handler
    if args.command == 'init':
        return cmd_init(args)
    elif args.command == 'up':
        return cmd_up(args)
    elif args.command == 'master':
        return cmd_master(args)
    elif args.command == 'worker':
        return cmd_worker(args)
    elif args.command == 'status':
        return cmd_status(args)
    elif args.command == 'down':
        return cmd_down(args)
    elif args.command == 'task':
        return cmd_task(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
