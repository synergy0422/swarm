"""
Tests for AutoRescuer main class.
"""
import os
import time
import unittest


class TestAutoRescuer(unittest.TestCase):
    """Test AutoRescuer main class functionality."""

    def setUp(self):
        from swarm.auto_rescuer import AutoRescuer
        self.rescuer = AutoRescuer(tmux_manager=None, dry_run=True)

    def test_auto_enter_patterns(self):
        """Test Press Enter pattern detection."""
        from swarm.auto_rescuer import AutoRescuer
        test_cases = [
            ("Press ENTER to continue...", True, 'auto_enter'),
            ("按回车继续", True, 'auto_enter'),
            ("hit enter to proceed", True, 'auto_enter'),
        ]
        for output, should_rescue, expected_action in test_cases:
            # Use unique window names to avoid cooldown
            rescuer = AutoRescuer(tmux_manager=None, dry_run=True)
            rescue, action, pattern = rescuer.check_and_rescue(output, f'window_{hash(output) % 10000}', 'session')
            self.assertEqual(action, expected_action, f"Failed on: {output}")

    def test_manual_confirm_patterns(self):
        """Test y/n, confirm patterns."""
        test_cases = [
            "Do you want to continue? [y/n]",
            "Please confirm your choice",
        ]
        for output in test_cases:
            rescue, action, pattern = self.rescuer.check_and_rescue(output, 'test', 'session')
            self.assertEqual(action, 'manual_confirm_needed')

    def test_dangerous_patterns(self):
        """Test dangerous command blacklist."""
        test_cases = [
            "rm -rf /tmp/data",
            "DROP DATABASE production",
        ]
        for output in test_cases:
            rescue, action, pattern = self.rescuer.check_and_rescue(output, 'test', 'session')
            self.assertEqual(action, 'dangerous_blocked')

    def test_no_pattern_returns_none(self):
        """No pattern match returns none."""
        output = "Normal output without prompts"
        rescue, action, pattern = self.rescuer.check_and_rescue(output, 'test', 'session')
        self.assertEqual(action, 'none')

    def test_cooldown_mechanism(self):
        """Test cooldown mechanism."""
        from swarm.auto_rescuer import AutoRescuer
        rescuer = AutoRescuer(tmux_manager=None, cooling_time=1.0, dry_run=True)
        # First trigger
        rescue, action, pattern = rescuer.check_and_rescue("Press ENTER", 'win1', 'session')
        self.assertTrue(rescue)
        # During cooldown
        rescue2, action2, _ = rescuer.check_and_rescue("Press ENTER", 'win1', 'session')
        self.assertEqual(action2, 'cooldown')
        # After cooldown
        time.sleep(1.1)
        rescue3, action3, _ = rescuer.check_and_rescue("Press ENTER", 'win1', 'session')
        self.assertTrue(rescue3)

    def test_disabled_via_env(self):
        """Test environment variable disable."""
        from swarm.auto_rescuer import AutoRescuer
        original = os.environ.get('AI_SWARM_AUTO_RESCUE_ENABLED')
        os.environ['AI_SWARM_AUTO_RESCUE_ENABLED'] = 'false'
        try:
            rescuer = AutoRescuer(dry_run=True)
            rescue, action, _ = rescuer.check_and_rescue("Press ENTER", 'test', 'session')
            self.assertEqual(action, 'disabled')
        finally:
            if original is None:
                os.environ.pop('AI_SWARM_AUTO_RESCUE_ENABLED', None)
            else:
                os.environ['AI_SWARM_AUTO_RESCUE_ENABLED'] = original

    def test_blocklist_config(self):
        """Test AI_SWARM_AUTO_RESCUE_BLOCK config."""
        from swarm.auto_rescuer import AutoRescuer
        original = os.environ.get('AI_SWARM_AUTO_RESCUE_BLOCK')
        os.environ['AI_SWARM_AUTO_RESCUE_BLOCK'] = 'special'
        try:
            rescuer = AutoRescuer(dry_run=True)
            rescue, action, _ = rescuer.check_and_rescue("special content here", 'test', 'session')
            self.assertEqual(action, 'blocked_by_config')
        finally:
            if original is None:
                os.environ.pop('AI_SWARM_AUTO_RESCUE_BLOCK', None)
            else:
                os.environ['AI_SWARM_AUTO_RESCUE_BLOCK'] = original

    def test_allowlist_config(self):
        """Test AI_SWARM_AUTO_RESCUE_ALLOW config."""
        from swarm.auto_rescuer import AutoRescuer
        original = os.environ.get('AI_SWARM_AUTO_RESCUE_ALLOW')
        os.environ['AI_SWARM_AUTO_RESCUE_ALLOW'] = 'special.*'
        try:
            rescuer = AutoRescuer(dry_run=True)
            # Match - content with allow pattern AND auto-enter pattern
            rescue, action, _ = rescuer.check_and_rescue("special content - Press ENTER to continue", 'test', 'session')
            self.assertEqual(action, 'auto_enter')
            # No match
            rescue2, action2, _ = rescuer.check_and_rescue("other content", 'test', 'session')
            self.assertEqual(action2, 'allowlist_missed')
        finally:
            if original is None:
                os.environ.pop('AI_SWARM_AUTO_RESCUE_ALLOW', None)
            else:
                os.environ['AI_SWARM_AUTO_RESCUE_ALLOW'] = original

    def test_stats_tracking(self):
        """Test statistics tracking."""
        from swarm.auto_rescuer import AutoRescuer
        rescuer = AutoRescuer(dry_run=True)
        rescuer.check_and_rescue("Press ENTER", 'w1', 's')
        rescuer.check_and_rescue("[y/n]", 'w2', 's')
        stats = rescuer.get_stats()
        self.assertEqual(stats['total_checks'], 2)
        self.assertEqual(stats['total_rescues'], 1)
        self.assertEqual(stats['manual_confirms'], 1)


if __name__ == '__main__':
    unittest.main()
