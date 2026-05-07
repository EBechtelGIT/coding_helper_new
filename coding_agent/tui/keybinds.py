"""Keyboard shortcut definitions for the TUI."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Keybind:
    """A keyboard shortcut definition."""
    key: str
    description: str
    action: str


# Leader key (like OpenCode's ctrl+x)
LEADER = "ctrl+x"

# Keybindings organized by category
KEYBINDS = {
    # Session management
    "new_session": Keybind(
        key=f"{LEADER} n",
        description="Create a new session",
        action="new_session",
    ),
    "list_sessions": Keybind(
        key=f"{LEADER} l",
        description="List and switch sessions",
        action="list_sessions",
    ),
    "switch_agent": Keybind(
        key="tab",
        description="Switch between agents (build/plan)",
        action="switch_agent",
    ),
    # Undo/Redo
    "undo": Keybind(
        key=f"{LEADER} u",
        description="Undo last message and changes",
        action="undo",
    ),
    "redo": Keybind(
        key=f"{LEADER} r",
        description="Redo undone message",
        action="redo",
    ),
    # UI toggles
    "toggle_details": Keybind(
        key=f"{LEADER} d",
        description="Toggle tool execution details",
        action="toggle_details",
    ),
    "toggle_theme": Keybind(
        key=f"{LEADER} t",
        description="Cycle through themes",
        action="toggle_theme",
    ),
    "command_palette": Keybind(
        key=f"{LEADER} p",
        description="Open command palette",
        action="command_palette",
    ),
    # Editor
    "open_editor": Keybind(
        key=f"{LEADER} e",
        description="Open external editor for message",
        action="open_editor",
    ),
    "export": Keybind(
        key=f"{LEADER} x",
        description="Export conversation to markdown",
        action="export",
    ),
    # Exit
    "exit": Keybind(
        key=f"{LEADER} q",
        description="Exit the application",
        action="exit",
    ),
    # Model selection
    "models": Keybind(
        key=f"{LEADER} m",
        description="List available models",
        action="models",
    ),
    # Help
    "help": Keybind(
        key="f1",
        description="Show help",
        action="help",
    ),
    # Scrolling
    "scroll_up": Keybind(
        key="up",
        description="Scroll up",
        action="scroll_up",
    ),
    "scroll_down": Keybind(
        key="down",
        description="Scroll down",
        action="scroll_down",
    ),
    "page_up": Keybind(
        key="pageup",
        description="Page up",
        action="page_up",
    ),
    "page_down": Keybind(
        key="pagedown",
        description="Page down",
        action="page_down",
    ),
    # Child session navigation
    "child_first": Keybind(
        key=f"{LEADER} down",
        description="Enter first child session",
        action="child_first",
    ),
    "child_next": Keybind(
        key="right",
        description="Next child session",
        action="child_next",
    ),
    "child_prev": Keybind(
        key="left",
        description="Previous child session",
        action="child_prev",
    ),
    "parent_session": Keybind(
        key="up",
        description="Return to parent session",
        action="parent_session",
    ),
}

# Inverse mapping for quick lookup
KEY_TO_ACTION = {kb.key: kb.action for kb in KEYBINDS.values()}


def get_keybind(action: str) -> Optional[Keybind]:
    """Get a keybind by action name."""
    return KEYBINDS.get(action)


def get_action(key: str) -> Optional[str]:
    """Get the action for a key combination."""
    return KEY_TO_ACTION.get(key)
