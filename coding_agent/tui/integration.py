"""Integration layer between TUI and the coding agent with streaming support."""

import asyncio
import os
from datetime import datetime
from pathlib import Path
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
from coding_agent.plan import Plan, parse_plan_from_text
from coding_agent.commands import get_custom_command, ensure_commands_dir
from langchain_core.messages import SystemMessage


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
        self._last_plan: Optional[Plan] = None

        ensure_skills_dir()
        ensure_commands_dir()
        self._init_question_tool()
        self._init_session()
        self._init_mcp()

    def _init_question_tool(self):
        from coding_agent.tools.question import set_question_callback

        def ask_question(header, question, options, multiple):
            result = None
            async def ask():
                nonlocal result
                screen = QuestionScreen(header, question, options, multiple)
                await self.tui_app.push_screen_wait(screen)
                result = screen.result
            import asyncio
            try:
                asyncio.run(ask())
            except RuntimeError:
                fut = asyncio.run_coroutine_threadsafe(ask(), asyncio.get_event_loop())
                import concurrent.futures
                try:
                    result = fut.result(timeout=120)
                except concurrent.futures.TimeoutError:
                    result = ["Timeout"]
            if result is None:
                result = []
            return result

        set_question_callback(ask_question)

    def _init_session(self):
        self.current_session = self.session_mgr.create_session(self.current_agent_name)
        if self.tui_app and hasattr(self.tui_app, '_status_bar') and self.tui_app._status_bar:
            self.tui_app._status_bar.session_id = self.current_session.id
            self.tui_app._status_bar.parent_session_id = ""

    def _init_mcp(self):
        try:
            config = load_mcp_config()
            if config.get("mcpServers"):
                self.mcp_manager = MCPServerManager()
        except Exception as e:
            if self.tui_app:
                self.tui_app.add_error(f"MCP init error: {e}")

    def _save_current_session_messages(self):
        """Sync current agent's chat_history into the session's messages list."""
        session = self.session_mgr.get_current()
        if not session:
            return
        agent = self.agent_instances.get(self.current_agent_name)
        if agent:
            session.messages = []
            for msg in agent.chat_history:
                session.add_message(msg)
            self.session_mgr.save_current()

    def _create_agent_for_config(self, agent_config: AgentConfig) -> CodingAgent:
        return self.get_or_create_agent(agent_config.name)

    def get_or_create_agent(self, agent_name: str) -> CodingAgent:
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

        agent_max_iter = agent_config.max_iterations or self.max_iterations or self.config.max_iterations

        agent = CodingAgent(
            llm=llm,
            tools=tools,
            max_iterations=agent_max_iter,
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
        self.tui_app.set_processing(True)
        try:
            if message.startswith("!"):
                if not self.config.allow_bash:
                    self.tui_app.add_system_message("Bash commands are disabled")
                    return
                return await self.handle_bash_command(message[1:].strip())

            if message.startswith("/"):
                await self._handle_custom_slash_command(message)
                return

            message = await self._process_file_references(message)

            self.tui_app.add_user_message(message)

            agent = self.get_or_create_agent(self.current_agent_name)

            if self._last_plan and self.current_agent_name == "build":
                plan_injection = self._last_plan.to_prompt_block()
                agent.chat_history.append(SystemMessage(content=plan_injection))
                self._last_plan = None

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

            if result.get("response"):
                plan = parse_plan_from_text(result["response"])
                if not plan.is_empty() and self.current_agent_name == "plan":
                    self._last_plan = plan
                    self.tui_app.call_from_thread(
                        self.tui_app.add_plan, result["response"]
                    )

            if not result.get("response"):
                if self.tui_app:
                    self.tui_app.add_error("Agent returned no response")

            # Persist chat_history to session storage
            self._save_current_session_messages()

            self.tui_app.add_separator()

        except Exception as e:
            self.tui_app.add_error(str(e))
            print_error(f"Error handling message: {e}")
        finally:
            self.tui_app.set_processing(False)

    async def _process_file_references(self, message: str) -> str:
        """Replace @file references with actual file contents."""
        import re
        def replace_ref(match):
            path = match.group(1).strip()
            full_path = Path(path)
            if not full_path.exists():
                full_path = Path.cwd() / path
            if full_path.exists() and full_path.is_file():
                try:
                    content = full_path.read_text(encoding="utf-8", errors="ignore")
                    preview = content[:200].replace("\n", " ").strip()
                    self.tui_app.call_from_thread(
                        self.tui_app.add_file_injection, str(full_path), preview
                    )
                    return f"\n--- File: {full_path} ---\n{content}\n--- End File ---\n"
                except Exception:
                    return f"@{path}"
            return f"@{path}"

        return re.sub(r'@(\S+)', replace_ref, message)

    async def _handle_custom_slash_command(self, command: str):
        """Handle custom slash commands defined by ``.opencode/commands/*.md``."""
        parts = command.strip().split()
        name = parts[0].lstrip("/").lower()
        payload = " ".join(parts[1:]) if len(parts) > 1 else ""

        builtins = {
            "help", "new", "list", "sessions", "clear", "undo", "redo",
            "export", "share", "exit", "quit", "switch", "compact",
            "models", "thinking", "themes", "theme", "init",
        }
        if name in builtins:
            self.tui_app.call_from_thread(
                self.tui_app._handle_slash_command, command
            )
            return

        prompt = get_custom_command(name)
        if prompt is None:
            self.tui_app.add_system_message(
                f"Unknown command: /{name}. Type /help or create .opencode/commands/{name}.md"
            )
            return

        filled = prompt.replace("{{input}}", payload) if "{{input}}" in prompt else prompt

        agent = self.get_or_create_agent(self.current_agent_name)
        agent.chat_history.append(SystemMessage(content=filled))
        self.tui_app.add_system_message(f"Custom command /{name} loaded")
        self.tui_app.add_separator()

    async def handle_file_reference(self, filepath: str):
        pass

    async def handle_bash_command(self, command: str) -> str:
        try:
            from coding_agent.tools.shell import run_bash_func
            result = run_bash_func(command)

            self.tui_app.add_user_message(f"!{command}")
            self.tui_app.add_tool_call("bash", command)
            self.tui_app.update_tool_result("bash", result, success=True)
            self.tui_app.add_separator()

            return result
        except Exception as e:
            error_msg = f"Bash command error: {e}"
            self.tui_app.add_error(error_msg)
            return error_msg

    async def _approval_prompt(self, tool_name: str, args_str: str) -> bool:
        try:
            if hasattr(self.tui_app, '_show_permission_dialog') and self.tui_app._chat_view:
                approved, deny_always = await self.tui_app._show_permission_dialog(tool_name, args_str)
                if deny_always:
                    self.permissions.deny_tool_permanently(tool_name)
                return approved
        except Exception:
            pass
        return True

    async def run_init(self):
        """Run /init: analyze project and generate/update AGENTS.md."""
        import subprocess
        agents_md_path = Path("AGENTS.md")
        existing = agents_md_path.read_text() if agents_md_path.exists() else ""

        project_info = []

        pyproject = Path("pyproject.toml")
        if pyproject.exists():
            project_info.append(f"Build system: Python (pyproject.toml)")

        package_json = Path("package.json")
        if package_json.exists():
            try:
                import json
                pkg = json.loads(package_json.read_text())
                project_info.append(f"Build system: Node.js ({pkg.get('name', 'unknown')})")
                if "scripts" in pkg:
                    project_info.append(f"Scripts: {json.dumps(pkg['scripts'], indent=2)}")
            except Exception:
                pass

        cargo = Path("Cargo.toml")
        if cargo.exists():
            project_info.append("Build system: Rust (Cargo.toml)")

        go_mod = Path("go.mod")
        if go_mod.exists():
            project_info.append("Build system: Go (go.mod)")

        docker = Path("Dockerfile")
        if docker.exists():
            project_info.append("Has Dockerfile")

        git_dir = Path(".git")
        if git_dir.exists():
            project_info.append("Git repository")

        readme = Path("README.md")
        if readme.exists():
            project_info.append("Has README.md")

        src_dirs = []
        for d in ["src", "app", "lib", "packages", "coding_agent"]:
            p = Path(d)
            if p.is_dir():
                py_files = list(p.rglob("*.py")) + list(p.rglob("*.ts")) + list(p.rglob("*.js"))
                src_dirs.append(f"{d}/ ({len(py_files)} source files)")

        dir_structure = []
        for entry in sorted(Path.cwd().iterdir()):
            if entry.name.startswith("."):
                continue
            if entry.is_dir():
                dir_structure.append(f"  {entry.name}/")
            else:
                dir_structure.append(f"  {entry.name}")

        content = f"""# Project Overview

{chr(10).join(project_info) if project_info else "Python project"}

## Project Structure

{chr(10).join(dir_structure)}

## Development

### Build/Test Commands
- Install: `pip install -e .` or `pip install -r requirements.txt`
- Run: `coding-agent` (or `python -m coding_agent.main`)
- Tests: `pytest tests/`

### Code Conventions
- Python >= 3.10
- Type hints required
- LangChain for LLM/tool abstractions
- Textual for TUI

## Configuration
- Global config: `~/.coding-agent/config.json`
- Project config: `.coding-agent.json`
- Project instructions: `AGENTS.md` (this file)
- Sessions stored in: `.coding-agent/sessions/`

## Agent Configuration
- Provider: Azure OpenAI (default)
- Agents: build (default), plan, general, explore
- Bash execution: disabled by default (enable with --allow-bash)

## Key Tools
- File operations: read, write, edit, patch
- Code search: glob, grep, list
- Web: search (DuckDuckGo), fetch (URL)
- Task management: todo list, subagent invocation
"""
        if existing:
            content = existing + "\n\n---\n\n" + content

        agents_md_path.write_text(content)

    def switch_agent(self, agent_name: str):
        if agent_name not in self.config.agents:
            self.tui_app.add_error(f"Unknown agent: {agent_name}")
            return
        self.current_agent_name = agent_name
        self.tui_app.current_agent = agent_name

    def new_session(self):
        # Save current session messages before creating new one
        self._save_current_session_messages()
        agent_name = self.current_agent_name
        self.current_session = self.session_mgr.create_session(agent_name)
        agent = self.get_or_create_agent(agent_name)
        agent.clear_history()
        if self.tui_app and hasattr(self.tui_app, '_status_bar') and self.tui_app._status_bar:
            self.tui_app._status_bar.session_id = self.current_session.id

    def list_sessions(self) -> list:
        return self.session_mgr.list_sessions()

    def load_session(self, session_id: str) -> Optional[Session]:
        session = self.session_mgr.load_session(session_id)
        if session:
            self.current_session = session
            self.current_agent_name = session.agent_name
            # Restore agent chat_history from session messages
            agent = self.get_or_create_agent(session.agent_name)
            agent.chat_history = session.get_messages()
            if self.tui_app and hasattr(self.tui_app, '_status_bar') and self.tui_app._status_bar:
                self.tui_app._status_bar.session_id = session.id
                self.tui_app._status_bar.parent_session_id = session.parent_id or ""
        return session

    def create_child_session(self, agent_name: str = "") -> Session:
        parent = self.session_mgr.get_current()
        agt = agent_name or self.current_agent_name
        child = self.session_mgr.create_session(agt)
        if parent:
            if parent.id != child.id:
                self.session_mgr.add_child(parent.id, child.id)
            parent_agent = self.agent_instances.get(self.current_agent_name)
            if parent_agent:
                parent_agent.chat_history = []
        return child

    def navigate_to_parent(self) -> bool:
        current = self.session_mgr.get_current()
        if not current or not current.parent_id:
            return False
        parent = self.session_mgr.get_session(current.parent_id)
        if not parent:
            return False
        # Save current session before navigating
        self._save_current_session_messages()
        self.session_mgr.set_current(parent)
        self.current_session = parent
        # Restore parent's agent history
        agent = self.get_or_create_agent(parent.agent_name)
        agent.chat_history = parent.get_messages()
        if self.tui_app and hasattr(self.tui_app, '_status_bar') and self.tui_app._status_bar:
            self.tui_app._status_bar.session_id = parent.id
            self.tui_app._status_bar.parent_session_id = parent.parent_id or ""
        return True

    def navigate_to_child(self) -> bool:
        current = self.session_mgr.get_current()
        if not current or not current.child_ids:
            return False
        child = self.session_mgr.get_session(current.child_ids[-1])
        if not child:
            return False
        # Save current session before navigating
        self._save_current_session_messages()
        self.session_mgr.set_current(child)
        self.current_session = child
        # Restore child's agent history
        agent = self.get_or_create_agent(child.agent_name)
        agent.chat_history = child.get_messages()
        if self.tui_app and hasattr(self.tui_app, '_status_bar') and self.tui_app._status_bar:
            self.tui_app._status_bar.session_id = child.id
            self.tui_app._status_bar.parent_session_id = child.parent_id or ""
        return True

    def list_sibling_sessions(self) -> list[Session]:
        current = self.session_mgr.get_current()
        if not current or not current.parent_id:
            siblings = [s for s in self.session_mgr.list_sessions() if s.id != (current.id if current else "")]
            return siblings[:5]
        parent = self.session_mgr.get_session(current.parent_id)
        if not parent:
            return []
        siblings = [self.session_mgr.get_session(cid) for cid in parent.child_ids]
        return [s for s in siblings if s and s.id != current.id]

    def compact_session(self):
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
        # Sync compacted messages back to agent's chat_history
        agent.chat_history = messages
        self.session_mgr.save_current()

    def export_session(self) -> Optional[str]:
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
            if role in ("human", "user"):
                lines.append(f"## User\n\n{content}\n")
            elif role in ("ai", "assistant"):
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
        return self.git_undo.undo()

    def redo(self) -> bool:
        return self.git_undo.redo()
