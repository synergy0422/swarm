"""
Custom exceptions for tmux swarm operations.
"""


class TmuxSwarmError(Exception):
    """Base exception for tmux swarm errors."""
    pass


class SessionNotFoundError(TmuxSwarmError):
    """Raised when a session is not found."""
    pass


class AgentNotFoundError(TmuxSwarmError):
    """Raised when an agent is not found."""
    pass


class PaneDeadError(TmuxSwarmError):
    """Raised when a pane is no longer alive."""
    pass


class SessionCreationError(TmuxSwarmError):
    """Raised when session creation fails."""
    pass
