#!/usr/bin/env python3
"""
Smart Worker Node with Anthropic API Integration

 DEPRECATED: This module is a thin wrapper for backwards compatibility.
 Use `from swarm import worker_smart` instead.
"""

# Re-export from swarm package for backwards compatibility
from swarm.worker_smart import SmartWorker

__all__ = ['SmartWorker']
