"""Integration layer between TUI and the coding agent with streaming support."""

import asyncio
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from coding_agent.agent import CodingAgent
from coding_agent.config import load_config, AgentConfig
from coding_agent.permissions import Permissions
from coding_agent.session import SessionManager, ContextCompactor, Session
from coding_agent.subagent import SubagentRunner
from coding_agent.prompts import get_system_prompt
from coding_agent.llm import create_llm, MockLLM
from coding_agent.tools import get_all_tools
from coding_agent.formatting import print_error
from coding_agent.git_undo import GitUndoManager
from coding_agent.mcp.config import load_mcp_config
from coding_agent.mcp.server_manager import MCPServerManager
from coding_agent.skills import ensure_skills_dir


class AgentTUIIntegration:
    """Bridges the TUI and the CodingAgent with streaming tool call display."""

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

        ensure_skills_dir()
        self._init_session()
        self._init_mcp()

    def _init_session(self):
        self.current_session = self.session_mgr.create_session(self.current_agent_name)

    def _init_mcp(self):
        try:
            config = load_mcp_config()
            if config.get("mcpServers"):
                self.mcp_manager = MCPServerManager()
        except Exception as e:
            if self.tui_app:
                self.tui_app.add_error(f"MCP init error: {e}")

    def _create_agent_for_config(self, agent_config: AgentConfig) -> CodingAgent:
        """Create an agent from an AgentConfig (used by subagent spawning)."""
        return self.get_or_create_agent(agent_config.name)

    def get_or_create_agent(self, agent_name: str) -> CodingAgent:
        """Get or create an agent instance."""
        if agent_name in self.agent_instances:
            return self.agent_instances[agent_name]

        agent_config = self.config.agents.get(
            agent_name, AgentConfig(name=agent_name, description="")
        )

        if agent_config.permission:
            self.permissions.apply_agent_config(agent_config.permission)

        tools = get_all_tools(
            disabled=self.config.tools_disabled,
            allow_bash=self.config.allow_bash,
            subagent_runner=self.subagent_runner,
            current_agent_name=agent_name,
            create_agent_fn=self._create_agent_for_config,
        )

        if self.mcp_manager:
            try:
                if hasattr(self.mcp_manager, 'get_all_langchain_tools'):
                    mcp_tools = self.mcp_manager.get_all_langchain_tools()
                    tools.extend(mcp_tools)
            except Exception as e:
                if self.tui_app:
                    self.tui_app.add_error(f"MCP tool load error: {e}")

        if agent_config.mode == "subagent":
            if agent_name == "explore":
                tools = [t for t in tools if t.name in {
                    'read_file', 'glob_search', 'grep_search',
                    'web_search', 'list_files', 'run_bash'
                }]

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

        system_prompt = get_system_prompt(agent_name, self.config)

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
        """Handle a user message with step-level streaming visibility."""
        self.tui_app.call_from_thread(self.tui_app.set_processing, True)
        try:
            if message.startswith("!"):
                return await self.handle_bash_command(message[1:].strip())

            self.tui_app.call_from_thread(self.tui_app.add_user_message, message)

            agent = self.get_or_create_agent(self.current_agent_name)

            # Build event callback that posts UI updates to the main thread
            def on_tool_call(name, args):
                self.tui_app.call_from_thread(
                    self.tui_app.add_tool_call, name, str(args)
                )

            def on_tool_result(name, result):
                self.tui_app.call_from_thread(
                    self.tui_app.update_tool_result, name, str(result)[:2000], True
                )

            def on_response(content):
                self.tui_app.call_from_thread(
                    self.tui_app.add_agent_message, content, self.current_agent_name
                )

            def on_thinking(content):
                self.tui_app.call_from_thread(
                    self.tui_app.add_thinking, content
                )

            result = await agent.run_turn_streaming(
                user_input=message,
                on_tool_call=on_tool_call,
                on_tool_result=on_tool_result,
                on_response=on_response,
                on_thinking=on_thinking,
            )

            # If no response callback was called (e.g. error), show it now
            if not result.get("response"):
                if self.tui_app:
                    self.tui_app.call_from_thread(
                        self.tui_app.add_error, "Agent returned no response"
                    )

            self.tui_app.call_from_thread(self.tui_app.add_separator)
            self.session_mgr.save_current()

        except Exception as e:
            self.tui_app.call_from_thread(self.tui_app.add_error, str(e))
            print_error(f"Error handling message: {e}")
        finally:
            self.tui_app.call_from_thread(self.tui_app.set_processing, False)

    async def handle_bash_command(self, command: str) -> str:
        """Handle a !bash command directly."""
        try:
            from coding_agent.tools.shell import run_bash_func
            result = run_bash_func(command)

            self.tui_app.add_user_message(f"!{command}")
            self.tui_app.add_tool_result(result, success=True)
            self.tui_app.add_separator()

            return result
        except Exception as e:
            error_msg = f"Bash command error: {e}"
            self.tui_app.add_error(error_msg)
            return error_msg

    async def _approval_prompt(self, tool_name: str, args_str: str) -> bool:
        """Show permission dialog in TUI."""
        try:
            if hasattr(self.tui_app, '_show_permission_dialog') and self.tui_app._chat_view:
                approved, deny_always = await self.tui_app._show_permission_dialog(tool_name, args_str)
                if deny_always:
                    self.permissions.deny_tool_permanently(tool_name)
                return approved
        except Exception:
            pass
        return True

    def switch_agent(self, agent_name: str):
        """Switch to a different agent."""
        if agent_name not in self.config.agents:
            self.tui_app.add_error(f"Unknown agent: {agent_name}")
            return
        self.current_agent_name = agent_name
        self.tui_app.current_agent = agent_name

    def new_session(self):
        """Create a new session."""
        agent_name = self.current_agent_name
        self.current_session = self.session_mgr.create_session(agent_name)
        agent = self.get_or_create_agent(agent_name)
        agent.clear_history()

    def list_sessions(self) -> list:
        """List all sessions."""
        return self.session_mgr.list_sessions()

    def load_session(self, session_id: str) -> Optional[Session]:
        """Load a session by ID."""
        session = self.session_mgr.load_session(session_id)
        if session:
            self.current_session = session
            self.current_agent_name = session.agent_name
        return session

    def compact_session(self):
        """Compact the current session."""
        session = self.session_mgr.get_current()
        if not session or session.message_count() < 10:
            return
        from coding_agent.session import ContextCompactor
        compactor = ContextCompactor()
        if not compactor.needs_compaction(session):
            return
        agent = self.get_or_create_agent(self.current_agent_name)
        messages = compactor.compact(session, getattr(agent, 'llm', None))
        session.messages = []
        for msg in messages:
            session.add_message(msg)
        self.session_mgr.save_current()

    def export_session(self) -> Optional[str]:
        """Export current session to a markdown file."""
        session = self.session_mgr.get_current()
        if not session:
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"session_{session.id[:8]}_{timestamp}.md"

        lines = [
            f"# Session: {session.id[:8]}",
            f"**Agent:** {session.agent_name}",
            f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Messages:** {session.message_count()}",
            "",
            "---",
            "",
        ]

        for msg in session.messages or []:
            role = msg.get("type", msg.get("role", "unknown"))
            content = msg.get("content", "")
            if role == "human" or role == "user":
                lines.append(f"## User\n\n{content}\n")
            elif role == "ai" or role == "assistant":
                lines.append(f"## {session.agent_name}\n\n{content}\n")
            elif role == "tool":
                lines.append(f"### Tool: {msg.get('name', 'unknown')}\n\n```\n{content}\n```\n")

        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            return filename
        except Exception as e:
            print_error(f"Export error: {e}")
            return None

    def undo(self) -> bool:
        """Undo last change."""
        return self.git_undo.undo()

    def redo(self) -> bool:
        """Redo last undone change."""
        return self.git_undo.redo()
