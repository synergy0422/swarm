"""Unit tests for enhanced PaneSummary with timestamp fields."""

import time
from swarm.master import PaneSummary


class TestPaneSummaryEnhancement:
    """Tests for enhanced PaneSummary with timestamp fields."""

    def test_pane_summary_new_fields_exist(self):
        """Verify PaneSummary has all new fields."""
        ps = PaneSummary('test-window')
        assert hasattr(ps, 'last_update_ts'), 'Missing last_update_ts'
        assert hasattr(ps, 'wait_since_ts'), 'Missing wait_since_ts'
        assert hasattr(ps, 'error_streak'), 'Missing error_streak'
        assert ps.error_streak == 0, 'error_streak should be 0'
        assert ps.wait_since_ts is None, 'wait_since_ts should be None initially'

    def test_error_streak_increments_on_consecutive_errors(self):
        """Verify error_streak increments on consecutive ERROR states."""
        ps = PaneSummary('test')
        ps.last_state = 'DONE'
        ps.error_streak = 0

        # First ERROR
        ps.update_state('ERROR', time.time())
        assert ps.error_streak == 1, 'error_streak should be 1 after first ERROR'

        # Second consecutive ERROR
        ps.update_state('ERROR', time.time())
        assert ps.error_streak == 2, 'error_streak should be 2 after second ERROR'

        # Third consecutive ERROR
        ps.update_state('ERROR', time.time())
        assert ps.error_streak == 3, 'error_streak should be 3 after third ERROR'

    def test_error_streak_resets_on_non_error_state(self):
        """Verify error_streak resets when leaving ERROR state."""
        ps = PaneSummary('test')
        ps.error_streak = 3
        ps.update_state('RUNNING', time.time())
        assert ps.error_streak == 0, 'error_streak should reset to 0'

    def test_wait_since_ts_set_on_enter_wait(self):
        """Verify wait_since_ts is set when entering WAIT state."""
        ps = PaneSummary('test')
        ps.wait_since_ts = None
        before = time.time()
        ps.update_state('WAIT', time.time())
        after = time.time()
        assert ps.wait_since_ts is not None, 'wait_since_ts should be set'
        assert before <= ps.wait_since_ts <= after, 'wait_since_ts should be current timestamp'

    def test_wait_since_ts_cleared_on_leave_wait(self):
        """Verify wait_since_ts is cleared when leaving WAIT state."""
        ps = PaneSummary('test')
        ps.wait_since_ts = time.time()
        ps.update_state('RUNNING', time.time())
        assert ps.wait_since_ts is None, 'wait_since_ts should be cleared'

    def test_timestamp_updated_on_state_change(self):
        """Verify last_update_ts updates on state change."""
        ps = PaneSummary('test')
        old_ts = ps.last_update_ts
        time.sleep(0.1)  # Small delay to ensure timestamp changes
        ps.update_state('ERROR', time.time())
        assert ps.last_update_ts > old_ts, 'last_update_ts should update on state change'

    def test_timestamp_updated_on_repeated_state(self):
        """Verify last_update_ts updates even on repeated same state."""
        ps = PaneSummary('test')
        ps.update_state('ERROR', time.time())
        first_ts = ps.last_update_ts
        time.sleep(0.1)
        ps.update_state('ERROR', time.time())
        assert ps.last_update_ts > first_ts, 'last_update_ts should update on consecutive ERROR'

    def test_error_streak_preserves_wait_since_ts(self):
        """Verify ERROR state does NOT clear wait_since_ts."""
        ps = PaneSummary('test')
        # First enter WAIT
        ps.update_state('WAIT', time.time())
        wait_ts = ps.wait_since_ts
        assert wait_ts is not None, 'wait_since_ts should be set'

        # Now get ERROR (consecutive error during wait)
        ps.update_state('ERROR', time.time())
        # wait_since_ts should NOT be cleared by ERROR
        assert ps.wait_since_ts == wait_ts, 'wait_since_ts should persist through ERROR'

    def test_state_updated_correctly(self):
        """Verify last_state is updated by update_state method."""
        ps = PaneSummary('test')
        ps.update_state('RUNNING', time.time())
        assert ps.last_state == 'RUNNING', 'last_state should be RUNNING'

        ps.update_state('WAIT', time.time())
        assert ps.last_state == 'WAIT', 'last_state should be WAIT'

    def test_format_timestamp(self):
        """Verify _format_timestamp produces HH:MM:SS format (local time)."""
        ps = PaneSummary('test')
        # Use a known timestamp
        ts = 1704067200  # 2024-01-01 00:00:00 UTC
        # In local timezone, the hour may differ from UTC
        # Just verify format is correct HH:MM:SS
        formatted = ps._format_timestamp(ts)
        import re
        assert re.match(r'\d{2}:\d{2}:\d{2}', formatted), f'Expected HH:MM:SS format, got {formatted}'

    def test_format_wait_duration_seconds(self):
        """Verify _format_wait_duration formats seconds correctly."""
        ps = PaneSummary('test')
        now = time.time()
        wait_start = now - 30  # 30 seconds ago
        formatted = ps._format_wait_duration(wait_start, now)
        assert formatted == '30s', f'Expected 30s, got {formatted}'

    def test_format_wait_duration_minutes(self):
        """Verify _format_wait_duration formats minutes correctly."""
        ps = PaneSummary('test')
        now = time.time()
        wait_start = now - 125  # 2 minutes 5 seconds ago
        formatted = ps._format_wait_duration(wait_start, now)
        assert formatted == '2m', f'Expected 2m, got {formatted}'

    def test_format_wait_duration_hours(self):
        """Verify _format_wait_duration formats hours correctly."""
        ps = PaneSummary('test')
        now = time.time()
        wait_start = now - 3725  # 1 hour 2 minutes 5 seconds ago
        formatted = ps._format_wait_duration(wait_start, now)
        assert formatted == '1h', f'Expected 1h, got {formatted}'

    def test_format_wait_duration_no_wait(self):
        """Verify _format_wait_duration returns dash for no wait or invalid timestamp."""
        ps = PaneSummary('test')
        now = time.time()
        # Test with negative timestamp (invalid)
        formatted = ps._format_wait_duration(-1, now)
        assert formatted == '-', f'Expected - for negative, got {formatted}'

        # Test with future timestamp (negative duration)
        formatted = ps._format_wait_duration(now + 100, now)
        assert formatted == '-', f'Expected - for future timestamp, got {formatted}'

    def test_initial_timestamp_is_recent(self):
        """Verify initial last_update_ts is recent (close to current time)."""
        ps = PaneSummary('test')
        now = time.time()
        assert abs(ps.last_update_ts - now) < 1, 'Initial timestamp should be recent'
