"""Theme definitions for the TUI, inspired by OpenCode."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Theme:
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
    diff_add: str = ""
    diff_remove: str = ""
    diff_hunk: str = ""
    thinking_bg: str = ""


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
        diff_add="#4ade80",
        diff_remove="#f87171",
        diff_hunk="#60a5fa",
        thinking_bg="#1c2128",
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
        diff_add="#9ece6a",
        diff_remove="#f7768e",
        diff_hunk="#7aa2f7",
        thinking_bg="#1f2335",
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
        diff_add="#16a34a",
        diff_remove="#dc2626",
        diff_hunk="#2563eb",
        thinking_bg="#f3f4f6",
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
        diff_add="#a6e22e",
        diff_remove="#f92672",
        diff_hunk="#66d9ef",
        thinking_bg="#3e3d32",
    ),
    "tokyonight": Theme(
        name="tokyonight",
        primary="#7aa2f7",
        secondary="#bb9af7",
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
        text_bright="#a9b1d6",
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
        diff_add="#9ece6a",
        diff_remove="#f7768e",
        diff_hunk="#7aa2f7",
        thinking_bg="#1f2335",
    ),
    "catppuccin": Theme(
        name="catppuccin",
        primary="#89b4fa",
        secondary="#cba6f7",
        background="#1e1e2e",
        surface="#313244",
        panel="#181825",
        user_label="#89b4fa",
        agent_label="#a6e3a1",
        tool_label="#fab387",
        error_label="#f38ba8",
        warning_label="#f9e2af",
        text="#cdd6f4",
        text_muted="#6c7086",
        text_bright="#ffffff",
        tool_output="#6c7086",
        tool_success="#a6e3a1",
        tool_error="#f38ba8",
        border="#45475a",
        separator="#313244",
        md_heading="#89b4fa",
        md_code="#a6e3a1",
        md_code_block="#a6e3a1",
        md_bold="#cdd6f4",
        md_italic="#cba6f7",
        md_link="#89b4fa",
        md_blockquote="#f9e2af",
        diff_add="#a6e3a1",
        diff_remove="#f38ba8",
        diff_hunk="#89b4fa",
        thinking_bg="#181825",
    ),
}

DEFAULT_THEME = "opencode"


def get_theme(name: Optional[str] = None) -> Theme:
    return THEMES.get(name or DEFAULT_THEME, THEMES[DEFAULT_THEME])
