"""
Tmux collaboration commands encapsulation - batch window operations.

Encapsulates the collaboration patterns from the reference:
- for w in $(tmux list-windows -a)
- tmux capture-pane -t "$w" -p -S -30
- tmux send-keys -t "0:$w" "y" Enter
"""

from typing import Dict, List, Optional
import libtmux


class TmuxCollaboration:
    """
    Tmux collaboration command encapsulation - batch window operations.

    Provides utilities for:
    - Listing all windows in a session
    - Capturing pane content from windows
    - Batch capturing all windows (for 4-window visualization)
    - Sending keys to specific windows
    """

    def __init__(self, server: Optional[libtmux.Server] = None):
        """
        Initialize TmuxCollaboration.

        Args:
            server: Optional libtmux Server instance. If not provided,
                   a new Server() will be created.
        """
        self.server = server or libtmux.Server()

    def list_windows(self, session_name: str) -> List[Dict]:
        """
        List all windows in a session.

        Args:
            session_name: Name of the tmux session to query.

        Returns:
            List of dictionaries containing window information:
            - name: Window name
            - index: Window index
            - activity: Activity timestamp or "unknown"
        """
        session = self.server.sessions.get(session_name=session_name, default=None)
        if not session:
            return []

        windows = []
        for w in session.windows:
            windows.append({
                "name": w.window_name,
                "index": w.window_index,
                "activity": getattr(w, "window_activity", "unknown"),
            })
        return windows

    def capture_pane(self, session_name: str, window_index: str) -> str:
        """
        Capture the content of a specific window's active pane.

        Args:
            session_name: Name of the tmux session.
            window_index: Index of the window to capture.

        Returns:
            String content of the pane, or empty string if session/window
            not found.
        """
        session = self.server.sessions.get(session_name=session_name, default=None)
        if not session:
            return ""

        window = session.windows.get(window_index=window_index, default=None)
        if not window:
            return ""

        result = window.active_pane.cmd("capture-pane", "-p", "-S", "-30")
        return "\n".join(result.stdout) if result.stdout else ""

    def capture_all_windows(self, session_name: str) -> Dict[str, str]:
        """
        Capture content from all windows in a session.

        This is the core function for the 4-window visualization feature,
        allowing real-time monitoring of all agent windows.

        Args:
            session_name: Name of the tmux session.

        Returns:
            Dictionary mapping window names to their pane content.
        """
        windows = self.list_windows(session_name)
        outputs = {}

        for w in windows:
            index = w["index"]
            name = w["name"]
            content = self.capture_pane(session_name, index)
            outputs[name] = content

        return outputs

    def send_keys_to_window(
        self,
        session_name: str,
        window_index: str,
        keys: str,
        enter: bool = True
    ) -> None:
        """
        Send keystrokes to a specific window's active pane.

        Args:
            session_name: Name of the tmux session.
            window_index: Index of the target window.
            keys: Keys to send (string).
            enter: If True, press Enter after sending keys (default: True).
        """
        session = self.server.sessions.get(session_name=session_name, default=None)
        if not session:
            return

        window = session.windows.get(window_index=window_index, default=None)
        if not window:
            return

        if enter:
            window.active_pane.send_keys(keys, enter=True)
        else:
            window.active_pane.send_keys(keys)
