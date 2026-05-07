"""Terminal formatting utilities for styled output.

Provides ANSI color/style helpers and functions to format user messages,
agent responses, tool calls, and errors in a way similar to Claude Code / OpenCode.
"""

import re
import sys
from typing import Optional

# ---------------------------------------------------------------------------
# ANSI helpers
# ---------------------------------------------------------------------------

class Style:
    """ANSI style codes."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"

    # Foreground 16-colour
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # Background (not used directly but kept for reference)
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"

    @staticmethod
    def rgb(r: int, g: int, b: int) -> str:
        """Return a 24-bit colour escape sequence (foreground)."""
        return f"\033[38;2;{r};{g};{b}m"

    @staticmethod
    def bg_rgb(r: int, g: int, b: int) -> str:
        """Return a 24-bit colour escape sequence (background)."""
        return f"\033[48;2;{r};{g};{b}m"


# ---------------------------------------------------------------------------
# Palette (Claude-Code-inspired defaults)
# ---------------------------------------------------------------------------

class Palette:
    """Central colour palette for the application."""

    # Primary / brand
    PRIMARY = Style.rgb(147, 51, 234)   # purple-ish (Claude accent)
    SECONDARY = Style.BRIGHT_CYAN

    # UI labels
    USER_LABEL = Style.rgb(59, 130, 246)   # blue
    AGENT_LABEL = Style.rgb(16, 185, 129)   # green
    TOOL_LABEL = Style.rgb(245, 158, 11)    # amber
    ERROR_LABEL = Style.rgb(239, 68, 68)    # red
    WARNING_LABEL = Style.rgb(251, 191, 36) # yellow

    # Text
    TEXT = Style.RESET + Style.rgb(229, 231, 235)
    TEXT_MUTED = Style.DIM + Style.rgb(156, 163, 175)
    TEXT_BRIGHT = Style.BRIGHT_WHITE

    # Tool output
    TOOL_OUTPUT = Style.DIM + Style.rgb(156, 163, 175)
    TOOL_SUCCESS = Style.rgb(74, 222, 128)
    TOOL_ERROR = Style.rgb(248, 113, 113)

    # Separators / borders
    BORDER = Style.rgb(75, 85, 99)
    SEPARATOR = Style.rgb(55, 65, 81)

    # Markdown
    MD_HEADING = Style.BOLD + Style.rgb(96, 165, 250)
    MD_CODE = Style.rgb(74, 222, 128)
    MD_CODE_BLOCK = Style.rgb(74, 222, 128)
    MD_BOLD = Style.BOLD + Style.rgb(255, 255, 255)
    MD_ITALIC = Style.ITALIC + Style.rgb(216, 180, 254)
    MD_LINK = Style.rgb(96, 165, 250)
    MD_BLOCKQUOTE = Style.rgb(251, 191, 36)


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def supports_color() -> bool:
    """Return True when the terminal likely supports ANSI colours."""
    return (
        hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
    ) or ("TERM" in __import__("os").environ and __import__("os").environ["TERM"] != "dumb")


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def s(text: str, *codes: str) -> str:
    """Wrap *text* with ANSI *codes* and a reset at the end.

    If the terminal does not support colour the codes are omitted.
    """
    if not supports_color():
        return text
    return "".join(codes) + text + Style.RESET


def bold(text: str) -> str:
    return s(text, Style.BOLD)


def dim(text: str) -> str:
    return s(text, Style.DIM)


def user_label() -> str:
    return s("You", Palette.USER_LABEL, Style.BOLD)


def agent_label(name: str) -> str:
    return s(name, Palette.AGENT_LABEL, Style.BOLD)


def session_label(session_id: str) -> str:
    return s(f"[{session_id}]", Palette.TEXT_MUTED, Style.DIM)


def subagent_label(name: str) -> str:
    return s(f"@{name}", Palette.SECONDARY, Style.BOLD)


def command_list(commands: list[str]) -> str:
    return s(" / ".join(commands), Palette.TEXT_MUTED, Style.DIM)


def permission_label(tool: str, action: str) -> str:
    colors = {
        "allow": Palette.TOOL_SUCCESS,
        "ask": Palette.WARNING_LABEL,
        "deny": Palette.TOOL_ERROR,
    }
    return s(f"{tool}: {action}", colors.get(action, Palette.TEXT))


def tool_label(name: str) -> str:
    return s(f"Tool: {name}", Palette.TOOL_LABEL, Style.BOLD)


def error_label() -> str:
    return s("Error", Palette.ERROR_LABEL, Style.BOLD)


# ---------------------------------------------------------------------------
# Markdown rendering  (very small subset – good enough for chat output)
# ---------------------------------------------------------------------------

def render_markdown(text: str) -> str:
    """Return *text* with basic markdown tokens replaced by ANSI styling.

    Supported:
    - `` `code` ``
    - `**bold**` / `__bold__`
    - `*italic*` / `_italic_`
    - `# Heading` (level-1 to 3)
    - `> blockquote`
    - `` ``` … ``` `` code blocks
    """
    if not supports_color():
        # Strip markdown for plain terminals
        text = re.sub(r"`([^`]+)`", r"\1", text)
        text = re.sub(r"\*\*(.+?)\*\*|__(.+?)__", r"\1\2", text)
        text = re.sub(r"\*(.+?)\*|_(.+?)_", r"\1\2", text)
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
        return text

    # Code blocks (``` ... ```) – treat as a block
    def _code_block(m: re.Match) -> str:
        code = m.group(1)
        lines = code.splitlines()
        out = []
        for line in lines:
            out.append(s(line, Palette.MD_CODE_BLOCK, Style.DIM))
        return "\n".join(out)

    text = re.sub(r"```.*?\n(.*?)```", _code_block, text, flags=re.DOTALL)

    # Inline code
    text = re.sub(
        r"`([^`]+)`",
        lambda m: s(m.group(1), Palette.MD_CODE, Style.DIM),
        text,
    )

    # Bold
    text = re.sub(
        r"\*\*(.+?)\*\*|__(.+?)__",
        lambda m: s(m.group(1) or m.group(2), Style.BOLD, Palette.MD_BOLD),
        text,
    )

    # Italic
    text = re.sub(
        r"\*(.+?)\*|_(.+?)_",
        lambda m: s(m.group(1) or m.group(2), Style.ITALIC, Palette.MD_ITALIC),
        text,
    )

    # Headings
    text = re.sub(
        r"^(#{1,3})\s+(.*)$",
        lambda m: s(m.group(2), Palette.MD_HEADING, Style.BOLD),
        text,
        flags=re.MULTILINE,
    )

    # Blockquote
    text = re.sub(
        r"^>\s?(.*)$",
        lambda m: s("│ " + m.group(1), Palette.MD_BLOCKQUOTE),
        text,
        flags=re.MULTILINE,
    )

    return text


# ---------------------------------------------------------------------------
# High-level printers
# ---------------------------------------------------------------------------

def print_user_message(message: str) -> None:
    """Pretty-print the user's input."""
    print(f"{user_label()}: {render_markdown(message)}")


def print_agent_message(message: str, agent_name: str = "Agent") -> None:
    print(f"{agent_label(agent_name)}: {render_markdown(message)}")


def print_tool_call(name: str, params: Optional[str] = None) -> None:
    """Print a tool invocation line."""
    line = f"  {tool_label(name)}"
    if params:
        line += f" {dim(params)}"
    print(line)


def print_tool_result(output: str, success: bool = True, max_lines: int = 20) -> None:
    """Print tool output, truncated to *max_lines* for readability."""
    color = Palette.TOOL_SUCCESS if success else Palette.TOOL_ERROR
    lines = output.splitlines()
    if len(lines) > max_lines:
        preview = lines[:max_lines]
        preview.append(f"... ({len(lines) - max_lines} more lines, truncated)")
    else:
        preview = lines
    for line in preview:
        print("  " + s(line, color, Style.DIM))
    print()  # blank line after tool block


def print_separator(char: str = "─", length: int = 50) -> None:
    """Print a horizontal separator."""
    print(s(char * length, Palette.SEPARATOR))


def print_plan(plan_content: str, plan_file: str) -> None:
    """Print plan with special formatting."""
    print(s(f"\n📋 Plan generated: {plan_file}", Palette.MD_HEADING))
    if plan_content:
        print(render_markdown(plan_content))
    print(s("─" * 50, Palette.SEPARATOR))


def print_error(message: str) -> None:
    """Print an error message."""
    print(f"{error_label()}: {s(message, Palette.TOOL_ERROR)}", file=sys.stderr)


def print_warning(message: str) -> None:
    """Print a warning message."""
    print(f"{s('Warning', Palette.WARNING_LABEL, Style.BOLD)}: {message}")


def print_banner(version: str = "0.3.0") -> None:
    """Print the startup banner."""
    print_separator("=")
    print(f"{s('Coding Agent', Palette.PRIMARY, Style.BOLD)} {s(f'v{version}', Palette.TEXT_MUTED)}")
    print_separator("=")
    print(f"  {dim('Type exit/quit to leave, clear to reset history')}")
    print()
