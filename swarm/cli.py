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


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='AI Swarm - Multi-Agent Task Processing System',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Global flags
    parser.add_argument(
        '--cluster-id',
        default=DEFAULT_CLUSTER_ID,
        help=f'Cluster identifier (default: {DEFAULT_CLUSTER_ID})'
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # init command
    subparsers.add_parser('init', help='Initialize swarm environment')

    # up command
    up_parser = subparsers.add_parser('up', help='Launch tmux session with master + workers')
    up_parser.add_argument(
        '--workers',
        type=int,
        default=DEFAULT_WORKERS,
        help=f'Number of worker processes (default: {DEFAULT_WORKERS})'
    )

    # master command
    subparsers.add_parser('master', help='Launch master process')

    # worker command
    worker_parser = subparsers.add_parser('worker', help='Launch single worker')
    worker_parser.add_argument(
        '--id',
        type=int,
        required=True,
        help='Worker ID (e.g., 1 for worker-1)'
    )

    # status command
    subparsers.add_parser('status', help='View swarm status')

    # down command
    subparsers.add_parser('down', help='Terminate swarm session')

    # Parse args
    args = parser.parse_args()

    # Route to command handler
    if args.command == 'init':
        return cmd_init(args)
    elif args.command == 'up':
        print("[ERROR] 'swarm up' not implemented yet - see Task 3")
        return 1
    elif args.command == 'master':
        return cmd_master(args)
    elif args.command == 'worker':
        return cmd_worker(args)
    elif args.command == 'status':
        print("[ERROR] 'swarm status' not implemented yet - see Task 4")
        return 1
    elif args.command == 'down':
        print("[ERROR] 'swarm down' not implemented yet - see Task 4")
        return 1
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
