"""
Pytest configuration for AI Swarm tests

Provides fixtures for test isolation.
"""

import pytest
import tempfile
import shutil
import os


@pytest.fixture(autouse=True)
def isolated_swarm_dir(monkeypatch):
    """
    Fixture that isolates each test by setting AI_SWARM_DIR to a temp directory.

    This ensures:
    - Tests don't pollute each other's state
    - Tests are repeatable (no leftover files between runs)
    - Tests don't depend on the actual /tmp/ai_swarm/ directory
    """
    temp_dir = tempfile.mkdtemp(prefix='ai_swarm_test_')
    monkeypatch.setenv('AI_SWARM_DIR', temp_dir)
    os.makedirs(temp_dir, exist_ok=True)
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)
