"""Chat view with agent-colored messages, syntax highlighting, collapsible thinking, and diffs."""

from typing import Optional

from textual.widgets import RichLog
from textual.containers import VerticalScroll
from textual.widgets import Collapsible, Label
from rich.text import Text
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.console import Group, RenderableType
from pygments.styles import get_style_by_name

from coding_agent.tui.themes import get_theme, Theme

try:
    import difflib
except ImportError:
    difflib = None

AGENT_COLORS = {
    "build": "green",
    "plan": "blue",
    "general": "magenta",
    "explore": "cyan",
}


def _get_agent_color(agent_name: str) -> str:
    return AGENT_COLORS.get(agent_name, "green")


def _make_diff_renderable(diff_text: str, theme: Theme) -> RenderableType:
    """Render a unified diff with syntax highlighting."""
    lines = diff_text.splitlines()
    rendered = []
    for line in lines:
        style = ""
        if line.startswith("+"):
            style = f"bold {theme.diff_add or 'green'}"
        elif line.startswith("-"):
            style = f"bold {theme.diff_remove or 'red'}"
        elif line.startswith("@@"):
            style = f"bold {theme.diff_hunk or 'cyan'}"
        elif line.startswith("diff --git") or line.startswith("index ") or line.startswith("---") or line.startswith("+++"):
            style = f"italic {theme.text_muted}"
        rendered.append(Text(line, style=style) if style else Text(line))
    return Group(*rendered)


class ChatView(VerticalScroll):
    """Chat display with agent colors, highlighted code, thinking blocks, and diffs."""

    def __init__(self, theme_name: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.theme = get_theme(theme_name)
        self._log: Optional[RichLog] = None
        self._tool_call_count = 0
        self._show_thinking = True

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
        label = Text(" You ", style=f"bold {theme.user_label or '#3b82f6'}")
        text = Text.assemble(label, " ", message)
        if self._log:
            self._log.write(text)

    def add_agent_message(self, message: str, agent_name: str = "Agent"):
        theme = self.theme
        color = _get_agent_color(agent_name)
        try:
            md = Markdown(
                message,
                code_theme=self._pygments_theme(),
                inline_code_theme=self._pygments_theme(),
            )
            panel = Panel(
                md,
                title=Text(f" {agent_name} ", style=f"bold {color}"),
                title_align="left",
                border_style=color,
                padding=(0, 1),
                subtitle=Text(f" {agent_name} ", style=f"bold {color}"),
                subtitle_align="right",
            )
            if self._log:
                self._log.write(panel)
        except Exception:
            label = Text(f" {agent_name} ", style=f"bold {color}")
            text = Text.assemble(label, " ", message)
            if self._log:
                self._log.write(text)

    def add_tool_call(self, name: str, params: str = ""):
        theme = self.theme
        self._tool_call_count += 1
        text = Text()
        text.append(f" \u23f3 {name}", style=f"bold {theme.tool_label or '#f59e0b'}")
        if params and len(params) < 200:
            text.append(f"  {params}", style=theme.text_muted or "#9ca3af")
        if self._log:
            self._log.write(text)

    def update_tool_result(self, name: str, result: str, success: bool = True):
        theme = self.theme
        result = str(result)
        lines = result.splitlines()
        display = "\n".join(lines[:10]) + ("\n..." if len(lines) > 10 else "")
        color = theme.tool_success or "green" if success else theme.tool_error or "red"
        text = Text(display, style=color)

        if name == "apply_patch" and len(lines) > 3 and any(l.startswith(("+", "-", "@@")) for l in lines[:20]):
            diff_renderable = _make_diff_renderable(result, theme)
            if self._log:
                self._log.write(diff_renderable)
            return

        if self._log:
            self._log.write(text)

    def add_thinking(self, content: str, agent_name: str = ""):
        if not self._show_thinking:
            return
        theme = self.theme
        color = _get_agent_color(agent_name)
        label = Text(f" {agent_name} ", style=f"bold {color}") if agent_name else Text("")
        thought = Text(f" {content}", style=f"italic {theme.text_muted or '#9ca3af'}")
        combined = Text.assemble(label, thought) if agent_name else thought
        if self._log:
            self._log.write(combined)

    def add_plan(self, plan_text: str):
        theme = self.theme
        try:
            md = Markdown(plan_text, code_theme=self._pygments_theme())
            panel = Panel(
                md,
                title=Text(" \U0001f4cb Plan ", style="bold blue"),
                title_align="left",
                border_style="blue",
                padding=(0, 1),
            )
            if self._log:
                self._log.write(panel)
        except Exception:
            text = Text(f"\U0001f4cb Plan:\n{plan_text}", style="blue")
            if self._log:
                self._log.write(text)

    def add_error(self, message: str):
        theme = self.theme
        text = Text()
        text.append(" Error: ", style=f"bold {theme.error_label or 'red'}")
        text.append(message, style=theme.tool_error or "red")
        if self._log:
            self._log.write(text)

    def add_separator(self):
        theme = self.theme
        if self._log:
            self._log.write(Rule(style=theme.separator or "#374151"))

    def add_system_message(self, message: str):
        """Add a system/info message (grayed out, non-conversational)."""
        theme = self.theme
        text = Text(message, style=f"italic {theme.text_muted or '#9ca3af'}")
        if self._log:
            self._log.write(text)

    def add_file_injection(self, filepath: str, content_preview: str):
        """Show that a file was injected via @ reference."""
        theme = self.theme
        text = Text()
        text.append(f" \U0001f4ce Injected: {filepath}", style=f"bold {theme.tool_label or '#f59e0b'}")
        if self._log:
            self._log.write(text)

    def clear(self):
        self._tool_call_count = 0
        if self._log:
            self._log.clear()

    def update_theme(self, theme_name: str):
        self.theme = get_theme(theme_name)

    def set_show_thinking(self, show: bool):
        self._show_thinking = show

    def _pygments_theme(self) -> str:
        bg = (self.theme.background or "#0d1117").lower()
        if bg in ("#0d1117", "#1a1b26", "#272822", "#282a36", "#002b36"):
            return "monokai"
        return "default"
