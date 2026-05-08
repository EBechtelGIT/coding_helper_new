"""Coding Agent - A local coding agent powered by LangChain.

This package provides a multi-agent coding assistant with TUI support.
"""

from coding_agent.agent import CodingAgent
from coding_agent.llm import create_llm
from coding_agent.config import load_config, AgentConfig
from coding_agent.permissions import Permissions
from coding_agent.session import SessionManager, ContextCompactor
from coding_agent.subagent import SubagentRunner
from coding_agent.prompts import get_system_prompt
from coding_agent.skills import load_skills, ensure_skills_dir, get_skills_prompt
from coding_agent.plan import Plan, parse_plan_from_text, plan_from_dict, FileChange
from coding_agent.formatting import (
    print_banner,
    print_user_message,
    print_agent_message,
    print_tool_call,
    print_tool_result,
    print_error,
    print_separator,
    print_plan,
)

__all__ = [
    "CodingAgent",
    "create_llm",
    "load_config",
    "AgentConfig",
    "Permissions",
    "SessionManager",
    "ContextCompactor",
    "SubagentRunner",
    "get_system_prompt",
    "print_banner",
    "print_user_message",
    "print_agent_message",
    "print_tool_call",
    "print_tool_result",
    "print_error",
    "print_separator",
    "print_plan",
]
