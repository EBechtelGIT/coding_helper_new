"""Chat view widget for displaying conversation history."""

from typing import List, Dict, Any, Optional
from textual.widgets import RichLog
from textual.containers import VerticalScroll
from textual.widget import Widget
from rich.text import Text

from coding_agent.tui.themes import get_theme, Theme


class ChatView(VerticalScroll):
    """A widget for displaying chat messages."""

    def __init__(self, theme_name: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.theme = get_theme(theme_name)
        self.messages: List[Dict[str, Any]] = []
        self._log: Optional[RichLog] = None

    def compose(self):
        """Compose the widget with a RichLog for messages."""
        self._log = RichLog(
            highlight=True,
            markup=True,
            wrap=True,
            auto_scroll=True,
        )
        yield self._log

    def add_user_message(self, message: str):
        """Add a user message to the chat."""
        theme = self.theme
        label = Text("You", style=f"bold {theme.user_label}")
        text = Text.assemble(label, " ", message)
        self.messages.append({"role": "user", "content": message})
        if self._log:
            self._log.write(text)

    def add_agent_message(self, message: str, agent_name: str = "Agent"):
        """Add an agent message to the chat."""
        theme = self.theme
        label = Text(agent_name, style=f"bold {theme.agent_label}")
        text = Text.assemble(label, " ", message)
        self.messages.append({"role": "assistant", "content": message, "agent": agent_name})
        if self._log:
            self._log.write(text)

    def add_tool_call(self, name: str, params: str):
        """Add a tool call indicator to the chat."""
        theme = self.theme
        text = Text()
        text.append("  Tool: ", style=theme.tool_label)
        text.append(name, style=f"bold {theme.tool_label}")
        if params:
            text.append(f" {params}", style=theme.text_muted)
        if self._log:
            self._log.write(text)

    def add_error(self, message: str):
        """Add an error message to the chat."""
        theme = self.theme
        text = Text()
        text.append("Error: ", style=f"bold {theme.error_label}")
        text.append(message, style=theme.tool_error)
        if self._log:
            self._log.write(text)

    def add_separator(self):
        """Add a visual separator between turns."""
        theme = self.theme
        text = Text("─" * 50, style=theme.separator)
        if self._log:
            self._log.write(text)

    def clear(self):
        """Clear all messages."""
        self.messages.clear()
        if self._log:
            self._log.clear()

    def update_theme(self, theme_name: str):
        """Update the theme."""
        self.theme = get_theme(theme_name)
