#!/usr/bin/env python3
"""
FIFO ACK Tracker - Track pending ACKs for FIFO dispatch.

Ensures Bridge doesn't falsely ACK when FIFO write succeeds but Master hasn't read.
Uses file-based tracking for persistence across Bridge restarts.
"""

import json
import os
import time
from datetime import datetime, timezone
from typing import Optional


class FifoAckTracker:
    """
    Track pending FIFO ACKs with file-based persistence.

    Flow:
    1. Bridge writes task to FIFO -> record_pending(task_id)
    2. Master reads FIFO -> mark_acked(task_id)
    3. Bridge polls until is_pending() returns False or timeout

    Storage format (JSONL):
    {"task_id": "br-123", "ts": "2026-02-07T10:00:00.000Z", "acked": false}
    {"task_id": "br-123", "ts": "2026-02-07T10:00:00.500Z", "acked": true}
    """

    def __init__(self, track_file: str):
        """
        Initialize ACK tracker.

        Args:
            track_file: Path to ACK tracking file (JSONL format)
        """
        self.track_file = track_file
        # Ensure directory exists
        os.makedirs(os.path.dirname(track_file), exist_ok=True)

    def record_pending(self, task_id: str) -> None:
        """
        Record a pending ACK for a task.

        Args:
            task_id: Bridge task ID to track
        """
        entry = {
            "task_id": task_id,
            "ts": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
            "acked": False
        }
        try:
            with open(self.track_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except (OSError, IOError) as e:
            print(f"[FifoAckTracker] Failed to record pending: {e}")

    def mark_acked(self, task_id: str) -> bool:
        """
        Mark a task as acknowledged (Master read it).

        Args:
            task_id: Bridge task ID to mark as acked

        Returns:
            True if marked, False if not found
        """
        # Read all entries, update matching one
        entries = []
        found = False

        if os.path.exists(self.track_file):
            try:
                with open(self.track_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        entry = json.loads(line)
                        if entry.get("task_id") == task_id:
                            entry["acked"] = True
                            entry["acked_ts"] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                            found = True
                        entries.append(entry)
            except (json.JSONDecodeError, OSError, IOError):
                return False

        if not found:
            return False

        # Write back
        try:
            with open(self.track_file, 'w') as f:
                for entry in entries:
                    f.write(json.dumps(entry) + '\n')
            return True
        except (OSError, IOError):
            return False

    def is_pending(self, task_id: str) -> bool:
        """
        Check if a task is still pending (not yet acked).

        Args:
            task_id: Bridge task ID to check

        Returns:
            True if pending, False if acked or not found
        """
        if not os.path.exists(self.track_file):
            return False

        try:
            with open(self.track_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    if entry.get("task_id") == task_id:
                        return not entry.get("acked", False)
            return False
        except (json.JSONDecodeError, OSError, IOError):
            return False

    def cleanup(self, max_age_seconds: float = 3600.0) -> int:
        """
        Clean up old entries from tracking file.

        Args:
            max_age_seconds: Maximum age in seconds (default: 1 hour)

        Returns:
            Number of entries removed
        """
        if not os.path.exists(self.track_file):
            return 0

        now = time.time()
        entries = []
        removed = 0

        try:
            with open(self.track_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    ts_str = entry.get("ts", "")
                    # Parse timestamp
                    try:
                        # Format: 2026-02-07T10:00:00.000Z
                        dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                        age = now - dt.timestamp()
                        if age < max_age_seconds:
                            entries.append(entry)
                        else:
                            removed += 1
                    except (ValueError, TypeError):
                        # Keep entries with invalid timestamps
                        entries.append(entry)
        except (json.JSONDecodeError, OSError, IOError):
            return 0

        # Write back
        try:
            with open(self.track_file, 'w') as f:
                for entry in entries:
                    f.write(json.dumps(entry) + '\n')
        except (OSError, IOError):
            pass

        return removed

    def get_all_pending(self) -> list:
        """
        Get all pending task IDs.

        Returns:
            List of pending task IDs
        """
        pending = []
        if not os.path.exists(self.track_file):
            return pending

        try:
            with open(self.track_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    if not entry.get("acked", False):
                        pending.append(entry.get("task_id"))
        except (json.JSONDecodeError, OSError, IOError):
            pass

        return pending
