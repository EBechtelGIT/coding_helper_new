"""Tools package for coding agent."""

from coding_agent.tools.file_ops import get_file_tools
from coding_agent.tools.file_search import get_search_tools
from coding_agent.tools.shell import get_shell_tools
from coding_agent.tools.web import get_web_tools
from coding_agent.tools.todo import get_todo_tools
from coding_agent.tools.task import get_task_tool


# Bash/python/git tools are opt-in (disabled by default for security).
DEFAULT_DISABLED_TOOLS = ["run_bash", "run_python", "run_git"]

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


def get_all_tools(disabled: list[str] = None, allow_bash: bool = False, subagent_runner=None, current_agent_name: str = "build", create_agent_fn=None):
    """Return all tools as LangChain StructuredTool instances.

    Args:
        disabled: List of tool names to exclude.
        allow_bash: If True, bash/python/git tools are included.
        subagent_runner: Optional SubagentRunner for the run_task tool.
        current_agent_name: Name of the current agent (for task tool).
        create_agent_fn: Callable(AgentConfig) -> CodingAgent for spawning subagents.
    """
    disabled = set(disabled or [])

    # If bash is not explicitly allowed, disable it by default
    if not allow_bash:
        disabled.update(DEFAULT_DISABLED_TOOLS)

    tools = []
    tools.extend(get_file_tools())
    tools.extend(get_search_tools())
    tools.extend(get_shell_tools())
    tools.extend(get_web_tools())
    tools.extend(get_todo_tools())

    # Add run_task tool if subagent_runner is provided
    if subagent_runner:
        tools.append(get_task_tool(subagent_runner, current_agent_name, create_agent_fn))

    return [t for t in tools if t.name not in disabled]


def get_tool_names() -> list[str]:
    """Return names of all available tools."""
    return [t.name for t in get_all_tools()]


def get_tools_by_category(category: str) -> list:
    """Return tools belonging to a specific category."""
    tool_names = TOOL_CATEGORIES.get(category, set())
    return [t for t in get_all_tools() if t.name in tool_names]
