"""
End-to-end tests for AutoRescuer workflow.
"""
import unittest
from unittest.mock import Mock, patch


class TestAutoRescuerE2E(unittest.TestCase):
    """End-to-end tests: complete workflow."""

    def setUp(self):
        from swarm.auto_rescuer import AutoRescuer
        self.mock_tmux = Mock()
        self.rescuer = AutoRescuer(tmux_manager=self.mock_tmux, dry_run=False)

    def test_full_auto_enter_workflow(self):
        """Full auto-enter rescue workflow."""
        # Setup mock
        self.mock_tmux.list_windows.return_value = [{'name': 'worker-0', 'index': 0}]

        # Trigger auto-enter
        rescue, action, pattern = self.rescuer.check_and_rescue(
            "Press ENTER to continue", 'worker-0', 'session'
        )

        # Verify rescue executed
        self.assertTrue(rescue)
        self.assertEqual(action, 'auto_enter')
        self.assertEqual(pattern, 'Press ENTER')

        # Verify tmux interaction
        self.mock_tmux.send_keys_to_window.assert_called()

    def test_no_action_in_dry_run_mode(self):
        """Dry-run mode should not call tmux."""
        from swarm.auto_rescuer import AutoRescuer
        mock_tmux = Mock()
        rescuer = AutoRescuer(tmux_manager=mock_tmux, dry_run=True)

        rescuer.check_and_rescue("Press ENTER", 'win1', 'session')

        # Should not call tmux in dry-run
        mock_tmux.send_keys_to_window.assert_not_called()

    def test_manual_confirm_no_rescue(self):
        """Manual confirm patterns should not trigger rescue."""
        rescue, action, pattern = self.rescuer.check_and_rescue(
            "Continue? [y/n]", 'worker-0', 'session'
        )

        self.assertFalse(rescue)
        self.assertEqual(action, 'manual_confirm_needed')
        self.mock_tmux.send_keys_to_window.assert_not_called()

    def test_dangerous_pattern_blocked(self):
        """Dangerous patterns should be blocked."""
        rescue, action, pattern = self.rescuer.check_and_rescue(
            "rm -rf /important/data", 'worker-0', 'session'
        )

        self.assertFalse(rescue)
        self.assertEqual(action, 'dangerous_blocked')
        self.mock_tmux.send_keys_to_window.assert_not_called()


if __name__ == '__main__':
    unittest.main()
