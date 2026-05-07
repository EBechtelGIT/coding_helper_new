"""Integration layer between TUI and the coding agent."""

import asyncio
from typing import Optional, Dict, Any, List
from coding_agent.agent import CodingAgent
from coding_agent.config import load_config, AgentConfig
from coding_agent.permissions import Permissions
from coding_agent.session import SessionManager, ContextCompactor
from coding_agent.subagent import SubagentRunner
from coding_agent.prompts import get_system_prompt
from coding_agent.llm import create_llm, MockLLM
from coding_agent.tools import get_all_tools
from coding_agent.formatting import print_error
from coding_agent.git_undo import GitUndoManager
from coding_agent.mcp.config import load_mcp_config
from coding_agent.mcp.server_manager import MCPServerManager


class AgentTUIIntegration:
    """Bridges the TUI and the CodingAgent."""

    def __init__(
        self,
        tui_app,
        verbose: bool = False,
        mock: bool = False,
        max_iterations: int = 15,
        plan_mode: bool = False,
        plan_file: str = "PLAN.md",
    ):
        self.tui_app = tui_app
        self.verbose = verbose
        self.mock = mock
        self.max_iterations = max_iterations
        self.plan_mode = plan_mode
        self.plan_file = plan_file

        self.config = load_config()
        self.session_mgr = SessionManager()
        self.subagent_runner = SubagentRunner()
        self.permissions = Permissions(approval_callback=self._approval_prompt)
        self.git_undo = GitUndoManager()

        self.current_agent_name = self.config.default_agent
        self.agent_instances: Dict[str, CodingAgent] = {}
        self.current_session = None
        self.mcp_manager = None

        # Initialize session
        self._init_session()
        # Initialize MCP if configured
        self._init_mcp()

    def _init_session(self):
        """Initialize or load session."""
        self.current_session = self.session_mgr.create_session(self.current_agent_name)

    def _init_mcp(self):
        """Initialize MCP servers from config."""
        try:
            config = load_mcp_config()
            if config.get("mcpServers"):
                self.mcp_manager = MCPServerManager()
                # Note: Would need to connect all servers here
                # For now, just store the config
        except Exception as e:
            if self.tui_app:
                self.tui_app.add_error(f"MCP init error: {e}")

    def get_or_create_agent(self, agent_name: str) -> CodingAgent:
        """Get or create an agent instance."""
        if agent_name in self.agent_instances:
            return self.agent_instances[agent_name]

        # Get agent config
        agent_config = self.config.agents.get(
            agent_name, AgentConfig(name=agent_name, description="")
        )

        # Apply permissions from config
        if agent_config.permission:
            self.permissions.apply_agent_config(agent_config.permission)

        # Get tools - pass subagent_runner for run_task tool
        tools = get_all_tools(
            disabled=self.config.tools_disabled,
            subagent_runner=self.subagent_runner,
            current_agent_name=agent_name,
        )

        # Add MCP tools if available
        if self.mcp_manager:
            try:
                if hasattr(self.mcp_manager, 'get_all_langchain_tools'):
                    mcp_tools = self.mcp_manager.get_all_langchain_tools()
                    tools.extend(mcp_tools)
            except Exception as e:
                if self.tui_app:
                    self.tui_app.add_error(f"MCP tool load error: {e}")

        # Restrict tools for subagents
        if agent_config.mode == "subagent":
            if agent_name == "explore":
                tools = [t for t in tools if t.name in {
                    'read_file', 'glob_search', 'grep_search', 
                    'web_search', 'list_files', 'run_bash'
                }]

        # Create LLM
        if self.mock:
            from coding_agent.llm import MockLLM
            llm = MockLLM(responses=[f"Hello from {agent_name} agent!"])
        else:
            llm = create_llm(
                tools=tools,
                provider=self.config.provider,
                model_name=agent_config.model or self.config.model,
                temperature=agent_config.temperature,
            )

        # Get system prompt
        system_prompt = get_system_prompt(agent_name, self.config)

        # Create agent
        agent = CodingAgent(
            llm=llm,
            tools=tools,
            max_iterations=self.max_iterations,
            verbose=self.verbose,
            planning_mode=self.plan_mode and agent_name == "plan",
            plan_file=self.plan_file,
            system_prompt=system_prompt,
            permissions=self.permissions,
        )

        self.agent_instances[agent_name] = agent
        return agent

    async def handle_user_message(self, message: str):
        """Handle a user message from the TUI."""
        try:
            # Check for !bash command
            if message.startswith("!"):
                return await self.handle_bash_command(message[1:].strip())

            # Add user message to TUI
            self.tui_app.add_user_message(message)

            # Get current agent
            agent = self.get_or_create_agent(self.current_agent_name)

            # Run the agent
            result = agent.run_turn(message)

            # Display tool calls
            if result.get("tool_calls"):
                for tc in result["tool_calls"]:
                    self.tui_app.add_tool_call(tc["name"], str(tc.get("params", "")))
                    if tc.get("result"):
                        self.tui_app.add_tool_result(tc["result"], success=True)

            # Display agent response
            self.tui_app.add_agent_message(
                result.get("response", ""),
                agent_name=self.current_agent_name
            )

            # Add separator
            self.tui_app.add_separator()

            # Save session
            self.session_mgr.save_current()

        except Exception as e:
            self.tui_app.add_error(str(e))
            print_error(f"Error handling message: {e}")

    async def handle_bash_command(self, command: str) -> str:
        """Handle a !bash command directly."""
        try:
            # Use the run_bash tool
            from coding_agent.tools.shell import run_bash
            result = run_bash(command)
            
            # Display in TUI
            self.tui_app.add_user_message(f"!{command}")
            self.tui_app.add_tool_result(result, success=True)
            self.tui_app.add_separator()
            
            return result
        except Exception as e:
            error_msg = f"Bash command error: {e}"
            self.tui_app.add_error(error_msg)
            return error_msg

    def switch_agent(self, agent_name: str):
        """Switch to a different agent."""
        if agent_name not in self.config.agents:
            self.tui_app.add_error(f"Unknown agent: {agent_name}")
            return

        self.current_agent_name = agent_name
        self.tui_app.current_agent = agent_name

        # Update status bar
        if hasattr(self.tui_app, '_status_label') and self.tui_app._status_label:
            self.tui_app._status_label.update(
                f"Agent: {agent_name} | Theme: {self.tui_app._theme_name}"
            )

    def undo(self) -> bool:
        """Undo last change (Git-based)."""
        return self.git_undo.undo()

    def redo(self) -> bool:
        """Redo last undone change."""
        return self.git_undo.redo()

    def _approval_prompt(self, tool_name: str, args_str: str) -> bool:
        """Callback for permission approval."""
        # In TUI mode, we need to handle this differently
        # For now, auto-approve (can be enhanced later with a dialog)
        self.tui_app.add_tool_call(tool_name, f"Permission requested: {args_str}")
        return True  # Auto-approve for now
