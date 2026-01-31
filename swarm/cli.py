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
import sys
import shutil
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
        print(f"[SWARM] Starting master for cluster: {args.cluster_id}")
        print("[SWARM] Press Ctrl+C to stop")
        master = Master()
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
        return server.find_session(session_name)
    except ImportError:
        return None
    except Exception:
        return None


def cmd_up(args):
    """
    Launch tmux session with master + N workers.

    Creates tmux session and spawns master and worker panes.
    """
    # Preflight checks
    if not check_tmux_installed():
        print("[ERROR] tmux not installed", file=sys.stderr)
        return 1

    if not check_libtmux_available():
        print("[ERROR] libtmux not installed", file=sys.stderr)
        print("Install: pip install libtmux", file=sys.stderr)
        return 1

    try:
        import libtmux
    except ImportError:
        print("[ERROR] libtmux not installed", file=sys.stderr)
        return 1

    session_name = f"swarm-{args.cluster_id}"

    # Check if session already exists
    server = libtmux.Server()
    existing_session = server.find_session(session_name)

    if existing_session:
        print(f"[ERROR] Swarm session already exists: {session_name}", file=sys.stderr)
        print(f"[ERROR] Run 'swarm down --cluster-id {args.cluster_id}' first", file=sys.stderr)
        return 1

    # Create new session
    print(f"[SWARM] Creating tmux session: {session_name}")

    try:
        session = server.new_session(session_name)

        # Create master pane
        print("[SWARM] Starting master pane...")
        master_window = session.new_window("master")
        master_pane = master_window.attached_pane
        master_pane.send_keys(f"python3 -m swarm.cli --cluster-id {args.cluster_id} master")

        # Create worker panes
        for i in range(args.workers):
            print(f"[SWARM] Starting worker-{i} pane...")
            worker_window = session.new_window(f"worker-{i}")
            worker_pane = worker_window.attached_pane
            worker_pane.send_keys(f"python3 -m swarm.cli --cluster-id {args.cluster_id} worker --id {i}")

        print(f"\n[SWARM] Swarm session created: {session_name}")
        print(f"[SWARM] Master + {args.workers} workers launched")
        print(f"\n[SWARM] Attach to session:")
        print(f"[SWARM]   tmux attach -t {session_name}")
        print(f"\n[SWARM] Check status:")
        print(f"[SWARM]   python3 -m swarm.cli --cluster-id {args.cluster_id} status")
        print(f"\n[SWARM] Stop swarm:")
        print(f"[SWARM]   python3 -m swarm.cli --cluster-id {args.cluster_id} down")

        return 0

    except Exception as e:
        print(f"[ERROR] Failed to create session: {e}", file=sys.stderr)
        print("[SWARM] Attempting cleanup...")
        # Try to cleanup
        cmd_down(args)
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
        print(f"[SWARM] No swarm session running: {session_name}")
        print(f"[SWARM] Run 'swarm up --cluster-id {args.cluster_id}' to start")
        return 0

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

    return 0


def cmd_down(args):
    """
    Terminate swarm session.

    Kills tmux session if it exists.
    """
    session_name = f"swarm-{args.cluster_id}"

    # Check if session exists
    session = get_session(args.cluster_id)

    if not session:
        print(f"[SWARM] No swarm session running: {session_name}")
        return 0

    try:
        # Kill session
        session.kill_session()
        print(f"[SWARM] Swarm session stopped: {session_name}")
        return 0
    except Exception as e:
        print(f"[ERROR] Failed to stop session: {e}", file=sys.stderr)
        return 1


def main():
    """Main CLI entry point"""
    # Parent parser for common arguments (shared across subcommands)
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        '--cluster-id',
        default=DEFAULT_CLUSTER_ID,
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
    subparsers.add_parser('status', parents=[parent_parser], help='View swarm status')

    # down command
    subparsers.add_parser('down', parents=[parent_parser], help='Terminate swarm session')

    # Parse args
    args = parser.parse_args()

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
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
