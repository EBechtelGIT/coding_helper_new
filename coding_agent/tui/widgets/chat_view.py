"""Chat view widget for displaying conversation history."""

from typing import List, Dict, Any, Optional
from textual.widgets import RichLog
from textual.containers import VerticalScroll
from textual.widget import Widget
from rich.text import Text
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.panel import Panel
from rich.rule import Rule
from pygments.util import ClassNotFound

from coding_agent.tui.themes import get_theme, Theme


class ChatView(VerticalScroll):
    """A widget for displaying chat messages."""

    def __init__(self, theme_name: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.theme = get_theme(theme_name)
        self.messages: List[Dict[str, Any]] = []
        self._log: Optional[RichLog] = None
        self._thinking_widget = None

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
        label = Text(f" {agent_name} ", style=f"bold {theme.agent_label}")
        try:
            md = Markdown(message, code_theme="monokai" if theme.background == "#272822" else "default")
            panel = Panel(md, title=agent_name, title_align="left", border_style=theme.agent_label, padding=(0, 1))
            if self._log:
                self._log.write(panel)
        except Exception:
            text = Text.assemble(label, " ", message)
            if self._log:
                self._log.write(text)
        self.messages.append({"role": "assistant", "content": message, "agent": agent_name})

    def add_tool_call(self, name: str, params: str = ""):
        theme = self.theme
        text = Text()
        text.append(f" \u23ef {name}", style=f"bold {theme.tool_label}")
        if params and len(params) < 200:
            text.append(f" {params}", style=theme.text_muted)
        if self._log:
            self._log.write(text)

    def add_tool_result(self, result: str, success: bool = True):
        theme = self.theme
        result = str(result)
        lines = result.splitlines()
        display = "\n".join(lines[:10]) + ("\n..." if len(lines) > 10 else "")
        color = theme.tool_success if success else theme.tool_error
        text = Text(display, style=color)
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

    def show_thinking(self, visible: bool = True):
        if self._log:
            if visible:
                self._log.write(Text(" \u23f3 Thinking...", style="italic #9ca3af"))
            else:
                pass

    def clear(self):
        self.messages.clear()
        if self._log:
            self._log.clear()

    def update_theme(self, theme_name: str):
        self.theme = get_theme(theme_name)