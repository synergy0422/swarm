#!/usr/bin/env python3
"""
Test suite for CLI dry-run and dangerous command detection

Tests for:
- swarm task run --dry-run flag
- stdout isolation (no pattern leaking)
- dangerous command warnings
"""

import subprocess
import sys
import tempfile
import os
from pathlib import Path


def run_cli(args, expected_exit=0):
    """Run CLI and return (stdout, stderr, exit_code)"""
    result = subprocess.run(
        [sys.executable, '-m', 'swarm.cli'] + args,
        capture_output=True,
        text=True
    )
    return result.stdout, result.stderr, result.returncode


class TestDryRun:
    """Test dry-run functionality"""

    def test_dry_run_echo(self):
        """Test: --dry-run with echo command"""
        stdout, stderr, code = run_cli(
            ['task', 'run', '--dry-run', 'test-worker', 'worker-0', 'echo', 'hello']
        )
        assert code == 0, f"Expected exit 0, got {code}"
        assert '[DRY-RUN] Would execute: echo hello' in stdout
        assert '[DRY-RUN] Task: test-worker on worker-0' in stdout

    def test_dry_run_true(self):
        """Test: --dry-run with true command"""
        stdout, stderr, code = run_cli(
            ['task', 'run', '--dry-run', 'test-worker', 'worker-0', 'true']
        )
        assert code == 0
        assert '[DRY-RUN] Would execute: true' in stdout

    def test_dry_run_multilevel_args(self):
        """Test: --dry-run with multiple command args"""
        stdout, stderr, code = run_cli(
            ['task', 'run', '--dry-run', 'test-worker', 'worker-0', 'echo', 'hello', 'world']
        )
        assert code == 0
        assert '[DRY-RUN] Would execute: echo hello world' in stdout

    def test_dry_run_no_lock_acquisition(self):
        """Test: --dry-run does not acquire locks or write status"""
        stdout, stderr, code = run_cli(
            ['task', 'run', '--dry-run', 'test-worker', 'worker-0', 'true']
        )
        # Should not attempt any lock operations
        assert 'Lock acquired' not in stdout + stderr
        assert 'Appended' not in stdout + stderr

    def test_dry_run_rm_dangerous(self):
        """Test: --dry-run shows dangerous rm command without executing"""
        stdout, stderr, code = run_cli(
            ['task', 'run', '--dry-run', 'test-worker', 'worker-0', 'rm', '-rf', '/tmp/test']
        )
        assert code == 0
        assert '[DRY-RUN] Would execute: rm -rf /tmp/test' in stdout
        # Should warn about dangerous command
        assert 'DANGEROUS COMMAND DETECTED' in stderr


class TestDangerousCommandDetection:
    """Test dangerous command detection and warnings"""

    def test_dangerous_patterns_warned(self):
        """Test: Various dangerous patterns trigger warnings"""
        dangerous_commands = [
            ['rm', '-rf', '/'],
            ['rm', '-rf', '/tmp'],
            ['dd', 'if=/dev/zero', 'of=/dev/sda'],
            ['mkfs.ext4', '/dev/sda'],
            ['shred', '-u', '/tmp/file'],
        ]

        for cmd in dangerous_commands:
            stdout, stderr, code = run_cli(
                ['task', 'run', '--dry-run', 'test-worker', 'worker-0'] + cmd
            )
            assert 'DANGEROUS COMMAND DETECTED' in stderr, f"Missing warning for: {' '.join(cmd)}"

    def test_safe_commands_no_warning(self):
        """Test: Safe commands don't trigger warnings"""
        safe_commands = [
            ['echo', 'hello'],
            ['true'],
            ['printf', 'hello'],
            ['ls', '-la'],
            ['cat', '/etc/hostname'],
        ]

        for cmd in safe_commands:
            stdout, stderr, code = run_cli(
                ['task', 'run', '--dry-run', 'test-worker', 'worker-0'] + cmd
            )
            assert 'DANGEROUS COMMAND DETECTED' not in stderr, f"False warning for: {' '.join(cmd)}"


class TestStdoutIsolation:
    """Test that dangerous patterns don't leak to stdout"""

    def test_no_pattern_in_stdout(self):
        """Test: Dangerous pattern should not appear in stdout"""
        stdout, stderr, code = run_cli(
            ['task', 'run', '--dry-run', 'test-worker', 'worker-0', 'rm', '-rf', '/tmp/test']
        )
        # stdout should only contain DRY-RUN output, not the pattern itself
        lines = [l for l in stdout.split('\n') if l.strip()]
        for line in lines:
            assert not line.startswith('rm -rf'), f"Pattern leaked to stdout: {line}"
            assert 'rm -rf' not in line or '[DRY-RUN]' in line, f"Pattern leaked to stdout: {line}"

    def test_clean_dry_run_output(self):
        """Test: Dry-run output is clean and parseable"""
        stdout, stderr, code = run_cli(
            ['task', 'run', '--dry-run', 'test-worker', 'worker-0', 'echo', 'hello']
        )
        # Output should be parseable - DRY-RUN lines
        assert stdout.count('[DRY-RUN]') == 2
        # No extra output between DRY-RUN lines
        dry_run_lines = [l for l in stdout.split('\n') if '[DRY-RUN]' in l]
        assert len(dry_run_lines) == 2


class TestWrapScriptDryRun:
    """Test wrap script --dry-run option directly"""

    def test_wrap_dry_run_flag(self):
        """Test: Wrap script --dry-run option"""
        result = subprocess.run(
            ['bash', 'scripts/swarm_task_wrap.sh', '--dry-run', 'run',
             'test-worker', 'worker-0', 'echo', 'hello'],
            capture_output=True,
            text=True,
            cwd='/home/user/projects/AAA/swarm'
        )
        assert result.returncode == 0
        # Use substring match since log_info adds timestamp prefix like [HH:MM:SS][INFO]
        assert 'DRY-RUN' in result.stderr
        assert 'Would execute: echo hello' in result.stderr

    def test_wrap_dry_run_dangerous(self):
        """Test: Wrap script warns about dangerous commands in dry-run"""
        result = subprocess.run(
            ['bash', 'scripts/swarm_task_wrap.sh', '--dry-run', 'run',
             'test-worker', 'worker-0', 'rm', '-rf', '/tmp/test'],
            capture_output=True,
            text=True,
            cwd='/home/user/projects/AAA/swarm'
        )
        assert result.returncode == 0
        # Use substring match for stability
        assert 'DANGEROUS COMMAND DETECTED' in result.stderr
        assert 'rm -rf' in result.stderr


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
