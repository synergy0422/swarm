"""
Tests for AutoRescuer pattern constants.
"""
import unittest


class TestAutoEnterPatterns(unittest.TestCase):
    """Test AUTO_ENTER_PATTERNS detection."""

    def test_press_enter_variants(self):
        from swarm.auto_rescuer import AutoRescuer
        test_cases = [
            "Press ENTER to continue",
            "Press Return",
            "Hit Enter to proceed",
            "按回车继续",
        ]
        for output in test_cases:
            # Use unique window names to avoid cooldown
            rescuer = AutoRescuer(dry_run=True)
            rescue, action, _ = rescuer.check_and_rescue(output, f'window_{hash(output) % 10000}', 'session')
            self.assertEqual(action, 'auto_enter', f"Failed on: {output}")


class TestManualConfirmPatterns(unittest.TestCase):
    """Test MANUAL_CONFIRM_PATTERNS detection."""

    def test_yn_patterns(self):
        from swarm.auto_rescuer import AutoRescuer
        rescuer = AutoRescuer(dry_run=True)
        test_cases = [
            "[y/n]",
            "[Y/n]",
            "(y/n)",
            "y or n",
        ]
        for output in test_cases:
            rescue, action, _ = rescuer.check_and_rescue(output, 'test', 'session')
            self.assertEqual(action, 'manual_confirm_needed', f"Failed on: {output}")

    def test_confirm_prompts(self):
        from swarm.auto_rescuer import AutoRescuer
        rescuer = AutoRescuer(dry_run=True)
        test_cases = [
            "Please confirm",
            "Are you sure",
            "确认",
            "确定吗",
        ]
        for output in test_cases:
            rescue, action, _ = rescuer.check_and_rescue(output, 'test', 'session')
            self.assertEqual(action, 'manual_confirm_needed', f"Failed on: {output}")

    def test_continue_proceed(self):
        from swarm.auto_rescuer import AutoRescuer
        rescuer = AutoRescuer(dry_run=True)
        test_cases = [
            "Continue? [Enter]",
            "Proceed with operation?",
        ]
        for output in test_cases:
            rescue, action, _ = rescuer.check_and_rescue(output, 'test', 'session')
            self.assertEqual(action, 'manual_confirm_needed', f"Failed on: {output}")


class TestDangerousPatterns(unittest.TestCase):
    """Test DANGEROUS_PATTERNS detection."""

    def test_rm_commands(self):
        from swarm.auto_rescuer import AutoRescuer
        rescuer = AutoRescuer(dry_run=True)
        test_cases = [
            "rm -rf /data",
            "rm -r /tmp/files",
            "rm -fr /var/log",
        ]
        for output in test_cases:
            rescue, action, _ = rescuer.check_and_rescue(output, 'test', 'session')
            self.assertEqual(action, 'dangerous_blocked', f"Failed on: {output}")

    def test_database_operations(self):
        from swarm.auto_rescuer import AutoRescuer
        rescuer = AutoRescuer(dry_run=True)
        test_cases = [
            "DROP DATABASE production",
            "DROP TABLE users",
            "TRUNCATE orders",
            "DELETE FROM transactions",
        ]
        for output in test_cases:
            rescue, action, _ = rescuer.check_and_rescue(output, 'test', 'session')
            self.assertEqual(action, 'dangerous_blocked', f"Failed on: {output}")


if __name__ == '__main__':
    unittest.main()
