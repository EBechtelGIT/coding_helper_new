"""Theme definitions for the TUI, inspired by OpenCode."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Theme:
    """A theme definition with colors for UI elements."""
    name: str
    primary: str
    secondary: str
    background: str
    surface: str
    panel: str
    user_label: str
    agent_label: str
    tool_label: str
    error_label: str
    warning_label: str
    text: str
    text_muted: str
    text_bright: str
    tool_output: str
    tool_success: str
    tool_error: str
    border: str
    separator: str
    md_heading: str
    md_code: str
    md_code_block: str
    md_bold: str
    md_italic: str
    md_link: str
    md_blockquote: str


# OpenCode-inspired themes
THEMES = {
    "opencode": Theme(
        name="opencode",
        primary="#9333ea",
        secondary="#06b6d4",
        background="#0d1117",
        surface="#161b22",
        panel="#1c2128",
        user_label="#3b82f6",
        agent_label="#10b981",
        tool_label="#f59e0b",
        error_label="#ef4444",
        warning_label="#fbbf24",
        text="#e5e7eb",
        text_muted="#9ca3af",
        text_bright="#ffffff",
        tool_output="#9ca3af",
        tool_success="#4ade80",
        tool_error="#f87171",
        border="#4b5563",
        separator="#374151",
        md_heading="#60a5fa",
        md_code="#4ade80",
        md_code_block="#4ade80",
        md_bold="#ffffff",
        md_italic="#d8b4fe",
        md_link="#60a5fa",
        md_blockquote="#fbbf24",
    ),
    "dark": Theme(
        name="dark",
        primary="#bb9af7",
        secondary="#7dcfff",
        background="#1a1b26",
        surface="#24283b",
        panel="#1f2335",
        user_label="#7aa2f7",
        agent_label="#9ece6a",
        tool_label="#e0af68",
        error_label="#f7768e",
        warning_label="#ff9e64",
        text="#c0caf5",
        text_muted="#565f89",
        text_bright="#ffffff",
        tool_output="#565f89",
        tool_success="#9ece6a",
        tool_error="#f7768e",
        border="#3b4261",
        separator="#2f3346",
        md_heading="#7aa2f7",
        md_code="#9ece6a",
        md_code_block="#9ece6a",
        md_bold="#c0caf5",
        md_italic="#bb9af7",
        md_link="#7aa2f7",
        md_blockquote="#ff9e64",
    ),
    "light": Theme(
        name="light",
        primary="#7c3aed",
        secondary="#0891b2",
        background="#ffffff",
        surface="#f9fafb",
        panel="#f3f4f6",
        user_label="#2563eb",
        agent_label="#059669",
        tool_label="#d97706",
        error_label="#dc2626",
        warning_label="#d97706",
        text="#111827",
        text_muted="#6b7280",
        text_bright="#000000",
        tool_output="#6b7280",
        tool_success="#16a34a",
        tool_error="#dc2626",
        border="#d1d5db",
        separator="#e5e7eb",
        md_heading="#2563eb",
        md_code="#16a34a",
        md_code_block="#16a34a",
        md_bold="#111827",
        md_italic="#7c3aed",
        md_link="#2563eb",
        md_blockquote="#d97706",
    ),
    "monokai": Theme(
        name="monokai",
        primary="#f8f8f2",
        secondary="#66d9ef",
        background="#272822",
        surface="#1e1f1c",
        panel="#3e3d32",
        user_label="#a6e22e",
        agent_label="#66d9ef",
        tool_label="#fd971f",
        error_label="#f92672",
        warning_label="#fd971f",
        text="#f8f8f2",
        text_muted="#75715e",
        text_bright="#ffffff",
        tool_output="#75715e",
        tool_success="#a6e22e",
        tool_error="#f92672",
        border="#3e3d32",
        separator="#75715e",
        md_heading="#66d9ef",
        md_code="#a6e22e",
        md_code_block="#a6e22e",
        md_bold="#f8f8f2",
        md_italic="#fd971f",
        md_link="#66d9ef",
        md_blockquote="#fd971f",
    ),
    "solarized": Theme(
        name="solarized",
        primary="#268bd2",
        secondary="#2aa198",
        background="#002b36",
        surface="#073642",
        panel="#0a3240",
        user_label="#268bd2",
        agent_label="#859900",
        tool_label="#b58900",
        error_label="#dc322f",
        warning_label="#cb4b16",
        text="#839496",
        text_muted="#657b83",
        text_bright="#fdf6e3",
        tool_output="#657b83",
        tool_success="#859900",
        tool_error="#dc322f",
        border="#073642",
        separator="#657b83",
        md_heading="#268bd2",
        md_code="#859900",
        md_code_block="#859900",
        md_bold="#839496",
        md_italic="#b58900",
        md_link="#268bd2",
        md_blockquote="#cb4b16",
    ),
    "dracula": Theme(
        name="dracula",
        primary="#bd93f9",
        secondary="#8be9fd",
        background="#282a36",
        surface="#44475a",
        panel="#3e404d",
        user_label="#8be9fd",
        agent_label="#50fa7b",
        tool_label="#ffb86c",
        error_label="#ff5555",
        warning_label="#f1fa8c",
        text="#f8f8f2",
        text_muted="#6272a4",
        text_bright="#ffffff",
        tool_output="#6272a4",
        tool_success="#50fa7b",
        tool_error="#ff5555",
        border="#44475a",
        separator="#6272a4",
        md_heading="#8be9fd",
        md_code="#50fa7b",
        md_code_block="#50fa7b",
        md_bold="#f8f8f2",
        md_italic="#ffb86c",
        md_link="#8be9fd",
        md_blockquote="#f1fa8c",
    ),
}

DEFAULT_THEME = "opencode"


def get_theme(name: Optional[str] = None) -> Theme:
    """Get a theme by name, or return the default theme."""
    return THEMES.get(name or DEFAULT_THEME, THEMES[DEFAULT_THEME])
