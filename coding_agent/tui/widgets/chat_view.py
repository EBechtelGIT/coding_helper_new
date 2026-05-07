"""Chat view widget for displaying conversation history with streaming support."""

from typing import List, Dict, Any, Optional
from textual.widgets import RichLog
from textual.containers import VerticalScroll
from rich.text import Text
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule

from coding_agent.tui.themes import get_theme, Theme


class ChatView(VerticalScroll):
    """A widget for displaying chat messages with real-time tool call updates."""

    def __init__(self, theme_name: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.theme = get_theme(theme_name)
        self.messages: List[Dict[str, Any]] = []
        self._log: Optional[RichLog] = None
        self._tool_call_count = 0

    def compose(self):
        self._log = RichLog(
            highlight=True,
            markup=True,
            wrap=True,
            auto_scroll=True,
        )
        yield self._log

    def add_user_message(self, message: str):
        theme = self.theme
        label = Text(" You ", style=f"bold {theme.user_label}")
        text = Text.assemble(label, " ", message)
        self.messages.append({"role": "user", "content": message})
        if self._log:
            self._log.write(text)

    def add_agent_message(self, message: str, agent_name: str = "Agent"):
        theme = self.theme
        try:
            md = Markdown(message, code_theme="monokai" if theme.background == "#272822" else "default")
            panel = Panel(md, title=agent_name, title_align="left", border_style=theme.agent_label, padding=(0, 1))
            if self._log:
                self._log.write(panel)
        except Exception:
            label = Text(f" {agent_name} ", style=f"bold {theme.agent_label}")
            text = Text.assemble(label, " ", message)
            if self._log:
                self._log.write(text)
        self.messages.append({"role": "assistant", "content": message, "agent": agent_name})

    def add_tool_call(self, name: str, params: str = ""):
        """Show a tool call entry immediately (appears in real-time)."""
        theme = self.theme
        self._tool_call_count += 1
        text = Text()
        text.append(f" \u23f3 {name}", style=f"bold {theme.tool_label}")
        if params and len(params) < 200:
            text.append(f"  {params}", style=theme.text_muted)
        if self._log:
            self._log.write(text)

    def update_tool_result(self, name: str, result: str, success: bool = True):
        """Update the most recent tool call with its result."""
        theme = self.theme
        result = str(result)
        lines = result.splitlines()
        display = "\n".join(lines[:10]) + ("\n..." if len(lines) > 10 else "")
        color = theme.tool_success if success else theme.tool_error
        text = Text(display, style=color)
        if self._log:
            self._log.write(text)

    def add_thinking(self, content: str):
        """Show thinking/reasoning text from the model (before tool calls)."""
        theme = self.theme
        text = Text(content, style=f"italic {theme.text_muted}")
        if self._log:
            self._log.write(text)

    def add_error(self, message: str):
        theme = self.theme
        text = Text()
        text.append(" Error: ", style=f"bold {theme.error_label}")
        text.append(message, style=theme.tool_error)
        if self._log:
            self._log.write(text)

    def add_separator(self):
        theme = self.theme
        if self._log:
            self._log.write(Rule(style=theme.separator))

    def clear(self):
        self.messages.clear()
        self._tool_call_count = 0
        if self._log:
            self._log.clear()

    def update_theme(self, theme_name: str):
        self.theme = get_theme(theme_name)
