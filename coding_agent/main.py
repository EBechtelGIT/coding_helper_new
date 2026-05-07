"""CLI entry point for the Coding Agent with multi-agent support."""

import argparse
import sys
import os
import readline
import asyncio

from coding_agent.agent import CodingAgent
from coding_agent.llm import create_llm, MockLLM
from coding_agent.tools import get_all_tools, get_tool_names
from coding_agent.config import load_config, AgentConfig
from coding_agent.permissions import Permissions
from coding_agent.session import SessionManager, ContextCompactor
from coding_agent.subagent import SubagentRunner
from coding_agent.prompts import get_system_prompt
from coding_agent.formatting import (
    print_banner,
    print_user_message,
    print_agent_message,
    print_tool_call,
    print_tool_result,
    print_error,
    print_separator,
    print_plan,
    session_label,
    subagent_label,
    command_list,
    permission_label,
)


SLASH_COMMANDS = [
    "/help", "/new", "/list", "/load", "/delete", "/clear",
    "/switch", "/agents", "/tools", "/permissions", "/compact",
    "/session", "/exit", "/quit",
]


def setup_readline():
    history_file = os.path.expanduser("~/.coding-agent/history")
    os.makedirs(os.path.dirname(history_file), exist_ok=True)
    try:
        readline.read_history_file(history_file)
    except FileNotFoundError:
        pass
    readline.set_history_length(10000)
    readline.parse_and_bind('tab: complete')
    return history_file


def completer(text, state):
    options = [cmd for cmd in SLASH_COMMANDS if cmd.startswith(text)]
    try:
        return options[state]
    except IndexError:
        return None


def main():
    parser = argparse.ArgumentParser(description="Coding Agent - Multi-agent coding assistant")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging to stderr")
    parser.add_argument("--max-iterations", type=int, default=15, help="Max tool-call iterations (default: 15)")
    parser.add_argument("--mock", action="store_true", help="Use mock LLM")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    parser.add_argument("--plan", action="store_true", help="Start with plan agent")
    parser.add_argument("--auto-execute", action="store_true", help="Auto-execute plans without approval")
    parser.add_argument("--plan-file", type=str, default="PLAN.md", help="Plan file path")
    parser.add_argument("--agent", type=str, default="", help="Start with specific agent")
    parser.add_argument("--session", type=str, default="", help="Load existing session")
    parser.add_argument("--no-compaction", action="store_true", help="Disable context compaction")
    parser.add_argument("--max-messages", type=int, default=50, help="Max messages before compaction")
    parser.add_argument("--tui", action="store_true", help="Launch the Textual TUI")
    parser.add_argument("--theme", type=str, default=None, help="TUI theme (opencode, dark, light)")
    args = parser.parse_args()

    if args.tui:
        asyncio.run(run_tui(args))
        return

    if args.no_color:
        import coding_agent.formatting as fmt
        for attr in dir(fmt.Palette):
            if not attr.startswith("_"):
                setattr(fmt.Palette, attr, "\033[0m")
        fmt.s = lambda text, *codes: text

    config = load_config()

    if args.no_compaction:
        compaction = None
    else:
        compaction = ContextCompactor(
            max_messages=args.max_messages or config.compaction_max_messages,
            compact_to=config.compaction_keep_messages,
        )

    session_mgr = SessionManager()
    subagent_runner = SubagentRunner()

    current_agent_name = args.agent or (args.plan and "plan") or config.default_agent
    permissions = Permissions(approval_callback=approval_prompt)

    if current_agent_name in config.agents:
        agent_config = config.agents[current_agent_name]
        if agent_config.permission:
            permissions.apply_agent_config(agent_config.permission)

    if args.session:
        session = session_mgr.load_session(args.session)
        if session:
            current_agent_name = session.agent_name
        else:
            print_error(f"Session not found: {args.session}")
            session = session_mgr.create_session(current_agent_name)
    else:
        session = session_mgr.create_session(current_agent_name)

    readline.set_completer(completer)
    history_file = setup_readline()

    agent_instances = {}

    def create_agent_for_config(agent_cfg):
        if agent_cfg.name in agent_instances:
            return agent_instances[agent_cfg.name]

        tools = get_all_tools(disabled=config.tools_disabled)

        if agent_cfg.mode == "subagent":
            restricted_tools = [t for t in tools if t.name in {'todowrite'}]
            if agent_cfg.name == "explore":
                tools = [t for t in tools if t.name in {'read_file', 'glob_search', 'grep_search', 'web_search', 'list_files', 'run_bash'}]

        if args.mock:
            llm = MockLLM(responses=[f"Hello from {agent_cfg.name} agent!"])
        else:
            llm = create_llm(
                tools=tools,
                provider=config.provider,
                model_name=agent_cfg.model or config.model,
                temperature=agent_cfg.temperature,
            )

        system_prompt = get_system_prompt(agent_cfg.name, config)

        agent = CodingAgent(
            llm=llm,
            tools=tools,
            max_iterations=args.max_iterations,
            verbose=args.verbose,
            planning_mode=args.plan and agent_cfg.name == "plan",
            plan_file=args.plan_file,
            system_prompt=system_prompt,
            permissions=permissions,
        )

        agent_instances[agent_cfg.name] = agent
        return agent

    active_agent = create_agent_for_config(config.agents.get(current_agent_name, AgentConfig(name=current_agent_name, description="")))

    print_banner()
    print(f"  Agent: {agent_label(current_agent_name)}  Session: {session_label(session.id)}")
    print(f"  {command_list(SLASH_COMMANDS)}")
    print()

    try:
        while True:
            session = session_mgr.get_current() or session_mgr.create_session(current_agent_name)

            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                readline.write_history_file(history_file)
                break

            if not user_input:
                continue

            if user_input.startswith("/"):
                handle_command(
                    user_input, config, session_mgr, subagent_runner,
                    permissions, compaction, agent_instances,
                    create_agent_for_config,
                )
                continue

            if user_input.lower() in ("exit", "quit"):
                print("Goodbye!")
                readline.write_history_file(history_file)
                break

            if user_input.lower() == "clear":
                session_mgr.create_session(current_agent_name)
                print("  New session created.")
                print()
                continue

            try:
                result = active_agent.run_turn(user_input)

                if result.get("tool_calls"):
                    for tc in result["tool_calls"]:
                        print_tool_call(tc["name"], tc["params"])
                        if tc.get("result"):
                            print_tool_result(tc["result"], success=True)

                print_agent_message(result["response"], current_agent_name)
                print_separator()

                session_mgr.save_current()

                if compaction and compaction.needs_compaction(session_mgr.get_current()):
                    compact_session(session_mgr, compaction, active_agent)

            except KeyboardInterrupt:
                print("\n  Interrupted.")
            except Exception as e:
                print_error(str(e))

    finally:
        try:
            readline.write_history_file(history_file)
        except Exception:
            pass


async def run_tui(args):
    """Run the TUI application."""
    from coding_agent.tui.app import CodingAgentApp
    from coding_agent.tui.themes import THEMES
    from coding_agent.tui.integration import AgentTUIIntegration

    config = load_config()

    # Validate theme
    theme_name = args.theme if args.theme in THEMES else "opencode"

    app = CodingAgentApp(
        theme_name=theme_name,
    )

    # Create integration layer
    integration = AgentTUIIntegration(
        tui_app=app,
        verbose=args.verbose,
        mock=args.mock,
        max_iterations=args.max_iterations,
        plan_mode=args.plan,
        plan_file=args.plan_file,
    )

    # Set the integration in the app
    app.set_integration(integration)

    # Set the input handler
    async def on_input(message: str):
        await integration.handle_user_message(message)

    app.set_input_handler(on_input)

    await app.run_async()


def handle_command(
    cmd, config, session_mgr, subagent_runner,
    permissions, compaction, agent_instances, create_fn,
):
    parts = cmd.split()
    command = parts[0].lower()

    if command == "/help":
        print_help()

    elif command == "/new":
        agent_name = parts[1] if len(parts) > 1 else session_mgr.get_current().agent_name
        session_mgr.create_session(agent_name)
        print(f"  New session created: {session_label(session_mgr.get_current().id)}")

    elif command == "/list":
        sessions = session_mgr.list_sessions()
        if not sessions:
            print("  No sessions.")
            return
        current = session_mgr.get_current()
        for s in sessions:
            marker = "*" if current and s.id == current.id else " "
            print(f"  {marker} {session_label(s.id)}  [{s.agent_name}]  {s.message_count()} msgs  {s.updated_at:.0f}")

    elif command == "/load":
        if len(parts) < 2:
            print_error("Usage: /load <session_id>")
            return
        session = session_mgr.load_session(parts[1])
        if session:
            print(f"  Loaded session: {session_label(session.id)}")
        else:
            print_error(f"Session not found: {parts[1]}")

    elif command == "/delete":
        if len(parts) < 2:
            print_error("Usage: /delete <session_id>")
            return
        if session_mgr.delete_session(parts[1]):
            print(f"  Session deleted: {parts[1]}")
        else:
            print_error(f"Session not found: {parts[1]}")

    elif command == "/switch":
        if len(parts) < 2:
            print_error("Usage: /switch <agent_name>")
            return
        agent_name = parts[1]
        if agent_name not in config.agents:
            print_error(f"Unknown agent: {agent_name}")
            print(f"  Available: {', '.join(a.name for a in config.list_agents())}")
            return
        print(f"  Switched to agent: {agent_name}")

    elif command == "/agents":
        print("  Available agents:")
        for a in config.list_agents():
            marker = ">" if a.mode == "primary" else "@"
            print(f"    {marker} {a.name}: {a.description}")

    elif command == "/tools":
        tools = get_tool_names()
        print(f"  Tools ({len(tools)}): {', '.join(tools)}")

    elif command == "/permissions":
        if len(parts) < 3:
            print("  Current permissions:")
            for cat, action in sorted(permissions.rules.items()):
                print(f"    {permission_label(cat, action)}")
            return
        if len(parts) < 3:
            print_error("Usage: /permissions <category> <allow|ask|deny>")
            return
        permissions.set_category(parts[1], parts[2])
        print(f"  Set {parts[1]}: {parts[2]}")

    elif command == "/compact":
        session = session_mgr.get_current()
        if session and compaction:
            compact_session(session_mgr, compaction, None)
            print("  Session compacted.")
        else:
            print("  Nothing to compact.")

    elif command == "/session":
        session = session_mgr.get_current()
        if session:
            print(f"  Session: {session_label(session.id)}")
            print(f"  Agent: {session.agent_name}")
            print(f"  Messages: {session.message_count()}")
            print(f"  Created: {session.created_at:.0f}")
            if session.parent_id:
                print(f"  Parent: {session.parent_id}")
            if session.child_ids:
                print(f"  Children: {', '.join(session.child_ids)}")

    else:
        print_error(f"Unknown command: {command}")
        print(f"  Type /help for available commands")


def print_help():
    print("  Commands:")
    print("    /help              Show this help")
    print("    /new [agent]       Create new session")
    print("    /list              List sessions")
    print("    /load <id>         Load session")
    print("    /delete <id>       Delete session")
    print("    /clear             Clear current session")
    print("    /switch <agent>    Switch agent")
    print("    /agents            List available agents")
    print("    /tools             List available tools")
    print("    /permissions       View/set permissions")
    print("    /compact           Compact session context")
    print("    /session           Show session info")
    print("    /exit, /quit       Exit")


def compact_session(session_mgr, compaction, agent):
    session = session_mgr.get_current()
    if not session or not compaction:
        return

    old_count = session.message_count()
    if not compaction.needs_compaction(session):
        return

    messages = compaction.compact(session, getattr(agent, 'llm', None))
    session.messages = []
    from langchain_core.messages import messages_to_dict, messages_from_dict
    for msg in messages:
        session.add_message(msg)

    session_mgr.save_current()


def approval_prompt(tool_name, args_str):
    print(f"\n  Permission requested: {tool_name} {args_str}")
    while True:
        resp = input("  Allow? [y/n/d(eny always)]: ").strip().lower()
        if resp in ("y", "yes"):
            return True
        if resp in ("n", "no"):
            return False
        if resp in ("d", "deny"):
            return False


if __name__ == "__main__":
    main()
