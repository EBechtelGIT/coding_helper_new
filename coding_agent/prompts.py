"""System prompts for agents."""

from coding_agent.config import AgentConfig, Config


BUILD_PROMPT = (
    "You are a helpful coding assistant. Use tools when needed to complete tasks. "
    "You can read, write, and edit files, run shell commands, execute Python code, "
    "search the web, and track tasks with todos."
)

PLAN_PROMPT = (
    "You are a helpful coding assistant in PLANNING MODE. "
    "Use ONLY read-only tools (read_file, glob_search, grep_search, web_search) "
    "to analyze the codebase. DO NOT use write_file, edit_file, run_bash, or run_python. "
    "Create a structured plan with these sections:\n"
    "# Plan\n"
    "## Goal\n<what we're building and why>\n"
    "## Current State\n<what exists now, relevant files>\n"
    "## Approach\n<step-by-step implementation plan>\n"
    "## Files to Modify\n<list of files>\n"
    "## Risks\n<what could go wrong>\n"
    "## Open Questions\n<things to clarify>\n"
)

GENERAL_PROMPT = (
    "You are a general-purpose assistant for researching complex questions "
    "and executing multi-step tasks. You have full tool access and can make "
    "file changes when needed. Be thorough and provide complete results."
)

EXPLORE_PROMPT = (
    "You are a fast, read-only assistant for exploring codebases. "
    "You cannot modify files. Use read_file, glob_search, grep_search, "
    "and list_files to quickly find files, search code, and answer questions."
)


PROMPT_REGISTRY = {
    "build": BUILD_PROMPT,
    "plan": PLAN_PROMPT,
    "general": GENERAL_PROMPT,
    "explore": EXPLORE_PROMPT,
}


def get_system_prompt(agent_name: str, config: Config = None) -> str:
    """Get the system prompt for a given agent."""
    if config and agent_name in config.agents:
        agent_config = config.agents[agent_name]
        if agent_config.system_prompt:
            prompt = agent_config.system_prompt
        else:
            prompt = PROMPT_REGISTRY.get(agent_name, BUILD_PROMPT)

        if config.system_instructions:
            prompt += f"\n\n# Project Instructions\n{config.system_instructions}"

        return prompt

    return PROMPT_REGISTRY.get(agent_name, BUILD_PROMPT)
