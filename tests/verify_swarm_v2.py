#!/usr/bin/env python3
"""
AI Swarm Phase 2 Verification Script

Automated end-to-end testing for the Phase 2 Smart Worker system.
Verifies dispatcher startup, task assignment, API integration, and cleanup.

Usage:
    python3 verify_swarm_v2.py [--duration SECONDS]
"""

import subprocess
import json
import time
import sys
import os
from pathlib import Path


# ANSI Color Codes
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color


class SwarmVerifierV2:
    """Verifies Phase 2 smart worker system functionality"""

    def __init__(self, script_dir=None, base_dir=None):
        """
        Initialize verifier

        Args:
            script_dir: Directory containing swarm_launcher_v2.sh
            base_dir: Directory containing tasks.json and status.log
        """
        if script_dir is None:
            script_dir = Path(__file__).parent
        self.script_dir = Path(script_dir)

        if base_dir is None:
            base_dir = os.path.expanduser('~/group/ai_swarm/')
        self.base_dir = base_dir

        self.launcher_script = self.script_dir / 'swarm_launcher_v2.sh'
        self.status_log = os.path.join(self.base_dir, 'status.log')
        self.tasks_file = os.path.join(self.base_dir, 'tasks.json')
        self.results_dir = os.path.join(self.base_dir, 'results')
        self.session_name = 'ai_swarm_v2'

        self.results = {
            'prerequisites': False,
            'startup': False,
            'task_dispatch': False,
            'api_integration': False,
            'result_generation': False,
            'cleanup': False,
        }

        self.metrics = {
            'total_lines': 0,
            'valid_json': 0,
            'tasks_assigned': 0,
            'tasks_completed': 0,
            'results_generated': 0,
            'runtime_seconds': 0,
        }

    def print_header(self):
        """Print test suite header"""
        title = "  AI Swarm Phase 2 - Smart Worker Verification"
        padding = 70 - len(title)
        print(f"\n{Colors.CYAN}╔{'═' * 70}╗{Colors.NC}")
        print(f"{Colors.CYAN}║{Colors.BOLD}{title}{Colors.NC}{' ' * padding}║")
        print(f"{Colors.CYAN}╚{'═' * 70}╝{Colors.NC}\n")

    def print_section(self, title):
        """Print section header"""
        print(f"\n{Colors.BLUE}{'─' * 70}{Colors.NC}")
        print(f"{Colors.BOLD}{Colors.BLUE}  {title}{Colors.NC}")
        print(f"{Colors.BLUE}{'─' * 70}{Colors.NC}\n")

    def check_prerequisites(self):
        """Check if required files and environment are ready"""
        self.print_section("Step 1: Prerequisites Check")

        checks = []

        # Check API key
        if os.environ.get('ANTHROPIC_API_KEY'):
            checks.append((True, "ANTHROPIC_API_KEY is set"))
        else:
            checks.append((False, "ANTHROPIC_API_KEY NOT set"))

        # Check launcher script
        if self.launcher_script.exists():
            checks.append((True, f"Launcher script: {self.launcher_script}"))
        else:
            checks.append((False, f"Launcher script NOT FOUND: {self.launcher_script}"))

        # Check if script is executable
        if os.access(self.launcher_script, os.X_OK):
            checks.append((True, "Launcher script is executable"))
        else:
            checks.append((False, "Launcher script is NOT executable"))

        # Check if tmux is available
        try:
            subprocess.run(['which', 'tmux'], capture_output=True, check=True)
            checks.append((True, "tmux is available"))
        except (subprocess.CalledProcessError, FileNotFoundError):
            checks.append((False, "tmux NOT found"))

        # Check Python dependencies
        try:
            subprocess.run(['python3', '-c', 'import requests'],
                          capture_output=True, check=True)
            checks.append((True, "Python requests module available"))
        except (subprocess.CalledProcessError, FileNotFoundError):
            checks.append((False, "Python requests module NOT found"))

        # Print results
        all_passed = True
        for passed, message in checks:
            status = f"{Colors.GREEN}✅{Colors.NC}" if passed else f"{Colors.RED}❌{Colors.NC}"
            print(f"  {status} {message}")
            if not passed:
                all_passed = False

        if not all_passed:
            print(f"\n{Colors.RED}❌ Prerequisites check failed. Aborting.{Colors.NC}")
            sys.exit(1)

        print(f"\n{Colors.GREEN}✅ All prerequisites met{Colors.NC}")
        self.results['prerequisites'] = True
        return True

    def kill_existing_session(self):
        """Kill any existing tmux session"""
        try:
            result = subprocess.run(
                ['tmux', 'has-session', '-t', self.session_name],
                capture_output=True,
                timeout=5
            )
            # Session exists, kill it
            print(f"{Colors.YELLOW}⚠️  Killing existing session...{Colors.NC}")
            subprocess.run(
                ['tmux', 'kill-session', '-t', self.session_name],
                capture_output=True,
                timeout=5
            )
            time.sleep(1)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            # Session doesn't exist, that's fine
            pass

    def setup_sample_tasks(self):
        """Create sample tasks.json if not exists"""
        self.print_section("Step 2: Setup Sample Tasks")

        if os.path.exists(self.tasks_file):
            print(f"  {Colors.GREEN}✅ Tasks file exists: {self.tasks_file}{Colors.NC}")
            return True

        print(f"  {Colors.YELLOW}Creating sample tasks.json...{Colors.NC}")

        sample_tasks = {
            "tasks": [
                {
                    "id": "task_001",
                    "prompt": "Write a haiku about artificial intelligence",
                    "status": "pending",
                    "priority": 1,
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 100
                },
                {
                    "id": "task_002",
                    "prompt": "Explain quantum computing in one paragraph",
                    "status": "pending",
                    "priority": 2,
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 150
                }
            ]
        }

        try:
            with open(self.tasks_file, 'w') as f:
                json.dump(sample_tasks, f, indent=2)
            print(f"  {Colors.GREEN}✅ Sample tasks created{Colors.NC}")
            return True
        except Exception as e:
            print(f"  {Colors.RED}❌ Error creating tasks: {e}{Colors.NC}")
            return False

    def launch_swarm(self):
        """Launch the swarm system"""
        self.print_section("Step 3: Launching Swarm")

        print(f"  📂 Script directory: {self.script_dir}")
        print(f"  📜 Launcher script: {self.launcher_script}")
        print(f"\n  {Colors.YELLOW}Starting swarm in detached mode...{Colors.NC}")

        try:
            # Launch in detached mode
            result = subprocess.run(
                ['bash', str(self.launcher_script), '--detach'],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.script_dir)
            )

            if result.returncode == 0:
                print(f"  {Colors.GREEN}✅ Swarm launched successfully{Colors.NC}")
                self.results['startup'] = True
                return True
            else:
                print(f"  {Colors.RED}❌ Launch failed{Colors.NC}")
                print(f"  Error: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print(f"  {Colors.RED}❌ Launch timed out{Colors.NC}")
            return False
        except Exception as e:
            print(f"  {Colors.RED}❌ Launch error: {e}{Colors.NC}")
            return False

    def wait_with_progress(self, duration_seconds=60):
        """Wait with countdown progress bar"""
        self.print_section(f"Step 4: Running Swarm ({duration_seconds}s)")

        print(f"  {Colors.CYAN}Letting workers process tasks...{Colors.NC}\n")

        for remaining in range(duration_seconds, 0, -1):
            # Calculate progress bar
            progress = int((duration_seconds - remaining) / duration_seconds * 40)
            bar = '█' * progress + '░' * (40 - progress)

            # Print progress
            print(f"\r  {Colors.GREEN}[{bar}]{Colors.NC} {remaining:2d}s remaining", end='', flush=True)
            time.sleep(1)

        print(f"\n\n  {Colors.GREEN}✅ Runtime complete{Colors.NC}")
        self.metrics['runtime_seconds'] = duration_seconds

    def analyze_logs_and_results(self):
        """Analyze status.log and results directory"""
        self.print_section("Step 5: Analyze Logs and Results")

        # Check status log
        if not os.path.exists(self.status_log):
            print(f"  {Colors.RED}❌ Status log not found: {self.status_log}{Colors.NC}")
            return False

        print(f"  📄 Reading status log...\n")

        # Read and parse status log
        entries = []
        with open(self.status_log, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entry = json.loads(line)
                        entries.append(entry)
                        self.metrics['valid_json'] += 1
                    except json.JSONDecodeError:
                        pass

        self.metrics['total_lines'] = len(entries)

        # Check for task dispatch signals
        dispatched = [e for e in entries if 'Assigned task' in e.get('msg', '')]
        self.metrics['tasks_assigned'] = len(dispatched)

        print(f"  📊 Log Analysis:")
        print(f"     Total log entries: {self.metrics['total_lines']}")
        print(f"     Tasks dispatched:   {self.metrics['tasks_assigned']}")

        # Check results directory
        if os.path.exists(self.results_dir):
            result_files = [f for f in os.listdir(self.results_dir) if f.endswith('.md')]
            self.metrics['results_generated'] = len(result_files)

            print(f"\n  📁 Results Directory:")
            print(f"     Result files: {self.metrics['results_generated']}")

            if result_files:
                for result_file in result_files[:3]:  # Show first 3
                    print(f"       - {result_file}")
                if len(result_files) > 3:
                    print(f"       ... and {len(result_files) - 3} more")
        else:
            print(f"\n  {Colors.YELLOW}⚠️  Results directory not found{Colors.NC}")

        # Update results
        self.results['task_dispatch'] = self.metrics['tasks_assigned'] > 0
        self.results['api_integration'] = 'START' in str([e.get('status') for e in entries])
        self.results['result_generation'] = self.metrics['results_generated'] > 0

        return True

    def cleanup(self):
        """Clean up tmux session"""
        self.print_section("Step 6: Cleanup")

        print(f"  🧹 Killing tmux session: {self.session_name}")

        try:
            result = subprocess.run(
                ['tmux', 'kill-session', '-t', self.session_name],
                capture_output=True,
                timeout=10
            )

            # Verify session is gone
            time.sleep(1)
            verify = subprocess.run(
                ['tmux', 'has-session', '-t', self.session_name],
                capture_output=True
            )

            if verify.returncode != 0:
                print(f"  {Colors.GREEN}✅ Session killed successfully{Colors.NC}")
                self.results['cleanup'] = True
            else:
                print(f"  {Colors.RED}❌ Session still running{Colors.NC}")

        except Exception as e:
            print(f"  {Colors.RED}❌ Cleanup error: {e}{Colors.NC}")

        return self.results['cleanup']

    def print_report(self):
        """Print final test report"""
        self.print_section("Test Report")

        # Overall score
        passed = sum(1 for v in self.results.values() if v)
        total = len(self.results)
        score = (passed / total) * 100

        print(f"\n  Overall Score: {score:.0f}%")
        print(f"  Tests Passed: {passed}/{total}")

        # Individual results
        print(f"\n  Test Results:")
        test_names = {
            'prerequisites': 'Prerequisites Check',
            'startup': 'Swarm Startup',
            'task_dispatch': 'Task Dispatch',
            'api_integration': 'API Integration',
            'result_generation': 'Result Generation',
            'cleanup': 'Session Cleanup',
        }

        for key, name in test_names.items():
            status = f"{Colors.GREEN}✅ PASS{Colors.NC}" if self.results[key] else f"{Colors.RED}❌ FAIL{Colors.NC}"
            print(f"     {status} {name}")

        # Metrics
        print(f"\n  Metrics:")
        print(f"     Runtime:            {self.metrics['runtime_seconds']}s")
        print(f"     Log entries:        {self.metrics['valid_json']}")
        print(f"     Tasks dispatched:   {self.metrics['tasks_assigned']}")
        print(f"     Results generated:  {self.metrics['results_generated']}")

        # Final verdict
        print(f"\n{Colors.CYAN}{'─' * 70}{Colors.NC}")

        if score == 100:
            print(f"\n  {Colors.GREEN}{Colors.BOLD}🎉 ALL TESTS PASSED! Phase 2 system is healthy.{Colors.NC}\n")
            return 0
        elif score >= 80:
            print(f"\n  {Colors.YELLOW}{Colors.BOLD}⚠️  MOSTLY PASSED ({score:.0f}%). Minor issues detected.{Colors.NC}\n")
            return 0
        else:
            print(f"\n  {Colors.RED}{Colors.BOLD}❌ TESTS FAILED ({score:.0f}%). System needs attention.{Colors.NC}\n")
            return 1

    def run(self, duration_seconds=60):
        """
        Run full verification test

        Args:
            duration_seconds: How long to let swarm run (default: 60)

        Returns:
            int: Exit code (0=success, 1=failure)
        """
        self.print_header()

        try:
            # Step 1: Check prerequisites
            if not self.check_prerequisites():
                return 1

            # Step 2: Kill any existing session
            self.kill_existing_session()

            # Step 3: Setup sample tasks
            if not self.setup_sample_tasks():
                return 1

            # Step 4: Launch swarm
            if not self.launch_swarm():
                self.cleanup()
                return 1

            # Step 5: Wait with progress bar
            self.wait_with_progress(duration_seconds)

            # Step 6: Analyze logs and results
            self.analyze_logs_and_results()

            # Step 7: Cleanup
            self.cleanup()

            # Step 8: Print report
            return self.print_report()

        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}⚠️  Test interrupted by user{Colors.NC}")
            self.cleanup()
            return 1
        except Exception as e:
            print(f"\n\n{Colors.RED}❌ Unexpected error: {e}{Colors.NC}")
            self.cleanup()
            return 1


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Verify AI Swarm Phase 2 System functionality'
    )
    parser.add_argument(
        '--duration',
        type=int,
        default=60,
        help='Swarm runtime in seconds (default: 60)'
    )
    parser.add_argument(
        '--script-dir',
        help='Directory containing swarm_launcher_v2.sh',
        default=None
    )
    parser.add_argument(
        '--base-dir',
        help='Directory containing tasks.json (default: ~/group/ai_swarm/)',
        default=None
    )

    args = parser.parse_args()

    verifier = SwarmVerifierV2(
        script_dir=args.script_dir,
        base_dir=args.base_dir
    )

    return verifier.run(duration_seconds=args.duration)


if __name__ == '__main__':
    sys.exit(main())
