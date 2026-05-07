"""Permission system for controlling agent tool access.

Supports three modes per tool category:
- "allow": tool can be used without approval
- "ask": user must approve each use
- "deny": tool is disabled
"""

from dataclasses import dataclass, field
from typing import Callable


TOOL_CATEGORIES = {
    "read": {"read_file"},
    "edit": {"write_file", "edit_file", "apply_patch"},
    "glob": {"glob_search"},
    "grep": {"grep_search"},
    "list": {"list_files"},
    "bash": {"run_bash"},
    "task": {"run_task"},
    "web": {"web_search", "web_fetch"},
    "todo": {"todowrite", "todoread"},
    "git": {"run_git"},
    "python": {"run_python"},
}


def tool_to_category(tool_name: str) -> str:
    """Map a tool name to its permission category."""
    for category, tools in TOOL_CATEGORIES.items():
        if tool_name in tools:
            return category
    return tool_name


@dataclass
class PermissionRule:
    """A single permission rule for a tool category or specific tool."""

    pattern: str
    action: str  # "allow", "ask", "deny"


@dataclass
class Permissions:
    """Permission manager for an agent session."""

    rules: dict[str, str] = field(default_factory=dict)
    denied_tools: set = field(default_factory=set)
    approval_callback: Callable = None

    def __init__(self, rules: dict[str, str] = None, approval_callback: Callable = None):
        self.rules = rules or {}
        self.denied_tools = set()
        self.approval_callback = approval_callback

    def set_category(self, category: str, action: str) -> None:
        """Set permission for a tool category."""
        self.rules[category] = action

    def set_tool(self, tool_name: str, action: str) -> None:
        """Set permission for a specific tool."""
        self.rules[tool_name] = action

    def deny_tool_permanently(self, tool_name: str) -> None:
        """Permanently deny a specific tool for this session."""
        self.denied_tools.add(tool_name)

    def get_action(self, tool_name: str) -> str:
        """Get the permission action for a tool.

        Returns 'allow', 'ask', or 'deny'.
        """
        if tool_name in self.denied_tools:
            return "deny"

        category = tool_to_category(tool_name)

        if tool_name in self.rules:
            return self.rules[tool_name]
        if category in self.rules:
            return self.rules[category]

        return "allow"

    def can_use(self, tool_name: str) -> bool:
        """Check if a tool can be used (allow or ask, not deny)."""
        return self.get_action(tool_name) != "deny"

    def needs_approval(self, tool_name: str) -> bool:
        """Check if a tool requires user approval."""
        return self.get_action(tool_name) == "ask"

    def check_and_approve(self, tool_name: str, tool_args: dict = None) -> bool:
        """Check permission and optionally prompt for approval.

        Returns True if the tool can proceed, False if denied.
        """
        if tool_name in self.denied_tools:
            return False

        action = self.get_action(tool_name)

        if action == "deny":
            return False

        if action == "allow":
            return True

        if action == "ask" and self.approval_callback:
            args_str = ""
            if tool_args:
                for k, v in list(tool_args.items())[:2]:
                    args_str += f"{k}={str(v)[:50]} "
            return self.approval_callback(tool_name, args_str.strip())

        return True

    def to_description(self) -> str:
        """Generate a description of current permissions for the system prompt."""
        if not self.rules:
            return "All tools are enabled."

        parts = []
        for category_or_tool, action in sorted(self.rules.items()):
            if action == "deny":
                parts.append(f"- {category_or_tool}: DENIED")
            elif action == "ask":
                parts.append(f"- {category_or_tool}: requires approval")

        if self.denied_tools:
            for t in sorted(self.denied_tools):
                parts.append(f"- {t}: DENIED")

        return "\n".join(parts) if parts else "All tools are enabled."

    def apply_agent_config(self, permission_data: dict) -> None:
        """Apply permissions from an AgentConfig.permission dict."""
        for key, value in permission_data.items():
            if isinstance(value, str):
                self.rules[key] = value
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    full_key = f"{key}:{sub_key}"
                    self.rules[full_key] = sub_value
