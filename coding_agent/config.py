"""Configuration loading from JSON files and AGENTS.md."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


GLOBAL_CONFIG_DIR = Path.home() / ".coding-agent"
GLOBAL_CONFIG_PATH = GLOBAL_CONFIG_DIR / "config.json"
PROJECT_CONFIG_PATH = Path(".coding-agent.json")
AGENTS_MD_PATH = Path("AGENTS.md")


@dataclass
class AgentConfig:
    """Configuration for a single agent."""

    name: str
    description: str
    mode: str = "primary"  # "primary" or "subagent"
    system_prompt: str = ""
    model: str = ""
    temperature: float = 0.0
    max_steps: int = 0               # Deprecated, use max_iterations
    max_iterations: int = 0          # 0 = use global default (Config.max_iterations)
    permission: dict = field(default_factory=dict)
    color: str = ""
    disabled: bool = False
    hidden: bool = False


@dataclass
class Config:
    """Full application configuration."""

    agents: dict[str, AgentConfig] = field(default_factory=dict)
    default_agent: str = "build"
    model: str = ""
    provider: str = "azure"
    max_iterations: int = 25
    compaction_max_messages: int = 50
    compaction_keep_messages: int = 20
    system_instructions: str = ""
    tools_disabled: list = field(default_factory=list)
    allow_bash: bool = False

    def get_agent(self, name: str) -> Optional[AgentConfig]:
        return self.agents.get(name)

    def list_agents(self) -> list[AgentConfig]:
        return [a for a in self.agents.values() if not a.disabled]

    def list_primary_agents(self) -> list[AgentConfig]:
        return [a for a in self.agents.values() if not a.disabled and a.mode == "primary"]

    def list_subagents(self) -> list[AgentConfig]:
        return [a for a in self.agents.values() if not a.disabled and a.mode == "subagent"]


def _load_global_config() -> dict:
    if GLOBAL_CONFIG_PATH.exists():
        try:
            with open(GLOBAL_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _load_project_config() -> dict:
    if PROJECT_CONFIG_PATH.exists():
        try:
            with open(PROJECT_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _load_agents_md() -> Optional[str]:
    if AGENTS_MD_PATH.exists():
        try:
            return AGENTS_MD_PATH.read_text(encoding="utf-8")
        except OSError:
            pass
    return None


def _parse_agent_from_json(name: str, data: dict) -> AgentConfig:
    return AgentConfig(
        name=name,
        description=data.get("description", ""),
        mode=data.get("mode", "primary"),
        system_prompt=data.get("prompt", ""),
        model=data.get("model", ""),
        temperature=data.get("temperature", 0.0),
        max_steps=data.get("max_steps", 0),
        max_iterations=data.get("max_iterations", 0),
        permission=data.get("permission", {}),
        color=data.get("color", ""),
        disabled=data.get("disabled", False),
        hidden=data.get("hidden", False),
    )


def _build_default_agents() -> dict[str, AgentConfig]:
    return {
        "build": AgentConfig(
            name="build",
            description="Default agent for development work with all tools enabled.",
            mode="primary",
        ),
        "plan": AgentConfig(
            name="plan",
            description="Read-only agent for analysis and code exploration.",
            mode="primary",
            permission={"edit": "deny", "bash": "deny"},
        ),
        "general": AgentConfig(
            name="general",
            description="General-purpose subagent for researching complex questions and executing multi-step tasks.",
            mode="subagent",
        ),
        "explore": AgentConfig(
            name="explore",
            description="Fast, read-only subagent for exploring codebases.",
            mode="subagent",
        ),
    }


def load_config() -> Config:
    """Load and merge global + project config with defaults."""
    global_cfg = _load_global_config()
    project_cfg = _load_project_config()
    agents_md = _load_agents_md()

    config = Config()

    agents = _build_default_agents()

    for source in [global_cfg, project_cfg]:
        agent_data = source.get("agent", {})
        for name, data in agent_data.items():
            agents[name] = _parse_agent_from_json(name, data)

        if source.get("default_agent"):
            config.default_agent = source["default_agent"]
        if source.get("model"):
            config.model = source["model"]
        if source.get("provider"):
            config.provider = source["provider"]
        if source.get("max_iterations"):
            config.max_iterations = source["max_iterations"]
        if source.get("compaction_max_messages"):
            config.compaction_max_messages = source["compaction_max_messages"]
        if source.get("compaction_keep_messages"):
            config.compaction_keep_messages = source["compaction_keep_messages"]
        if source.get("tools_disabled"):
            config.tools_disabled = source["tools_disabled"]
        if source.get("allow_bash"):
            config.allow_bash = True

    # If bash is explicitly allowed, remove bash tools from disabled list
    if config.allow_bash:
        from coding_agent.tools import DEFAULT_DISABLED_TOOLS
        config.tools_disabled = [t for t in config.tools_disabled if t not in DEFAULT_DISABLED_TOOLS]

    if agents_md:
        config.system_instructions = agents_md

    config.agents = agents
    return config
