"""Main TUI application using Textual."""

import os
import tempfile
import subprocess
from datetime import datetime
from typing import Optional, Callable, Dict, Any, List

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Footer, Label, ListView, ListItem, Button, Static
from textual.screen import ModalScreen, Screen
from textual.reactive import reactive
from textual import events

from coding_agent.tui.themes import get_theme, THEMES, DEFAULT_THEME
from coding_agent.tui.widgets.input_bar import InputBar
from coding_agent.tui.widgets.chat_view import ChatView
from coding_agent.tui.widgets.status_bar import StatusBar


class PermissionScreen(ModalScreen):
    """Modal screen for tool permission approval."""

    def __init__(self, tool_name: str, args_str: str, on_result: Callable[[bool, bool], None], **kwargs):
        super().__init__(**kwargs)
        self._tool_name = tool_name
        self._args_str = args_str
        self._on_result = on_result

    def compose(self):
        yield Container(
            Label("Permission Request", classes="permission-title"),
            Label(f"Tool: {self._tool_name}", classes="permission-tool"),
            Label(f"Args: {self._args_str[:200]}", classes="permission-args"),
            Horizontal(
                Button("Allow", variant="primary", id="allow"),
                Button("Deny", id="deny"),
                Button("Deny Always", variant="error", id="deny-always"),
                classes="permission-buttons",
            ),
            id="permission-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "allow":
            self._on_result(True, False)
        elif event.button.id == "deny":
            self._on_result(False, False)
        elif event.button.id == "deny-always":
            self._on_result(False, True)
        self.dismiss()


class HelpScreen(Screen):
    """Help screen with keybindings reference."""

    def compose(self):
        yield Container(
            Label("Help & Keybindings", classes="help-title"),
            Label("Session Management", classes="help-section"),
            Label("  Ctrl+X N    New session"),
            Label("  Ctrl+X L    List sessions"),
            Label("  Tab         Switch agent (build/plan)"),
            Label("Undo/Redo", classes="help-section"),
            Label("  Ctrl+X U    Undo last change"),
            Label("  Ctrl+X R    Redo last undo"),
            Label("UI", classes="help-section"),
            Label("  Ctrl+X T    Toggle theme"),
            Label("  Ctrl+X P    Command palette"),
            Label("  Ctrl+X D    Toggle tool details"),
            Label("  F1         Show this help"),
            Label("General", classes="help-section"),
            Label("  Ctrl+X E    Open editor (multi-line input)"),
            Label("  Ctrl+X X    Export conversation"),
            Label("  Ctrl+X M    Show model info"),
            Label("  Ctrl+X Q    Exit"),
            Label("Commands", classes="help-section"),
            Label("  /help       Show help"),
            Label("  /new        New session"),
            Label("  /list       List sessions"),
            Label("  /switch     Switch agent"),
            Label("  /undo       Undo last change"),
            Label("  /redo       Redo last undo"),
            Label("  /clear      Clear chat"),
            Label("  /export     Export conversation"),
            Label("  /compact    Compact session"),
            Label("  /exit       Exit"),
            Label("  @file       Reference a file in your prompt"),
            Label("  !command   Run a bash command directly"),
            Label(""),
            Label("Press any key to close", classes="help-hint"),
            id="help-container",
        )

    def on_key(self, event: events.Key):
        self.app.pop_screen()


class SessionListScreen(ModalScreen):
    """Modal screen to list and switch sessions."""

    def __init__(self, sessions: List[Dict[str, Any]], on_select: Callable[[str], None], **kwargs):
        super().__init__(**kwargs)
        self._sessions = sessions
        self._on_select = on_select

    def compose(self):
        yield Container(
            Label("Sessions", classes="session-list-title"),
            id="session-list-container",
        )

    def on_mount(self):
        container = self.query_one("#session-list-container")
        if not self._sessions:
            container.mount(Label("No sessions"))
            return
        lv = ListView(id="session-list-view")
        for s in self._sessions:
            label = f"[{s.get('id', '?')[:8]}] {s.get('agent_name', '?')}  {s.get('message_count', 0)} msgs"
            lv.append(ListItem(Label(label)))
        container.mount(lv)

    def on_list_view_selected(self, event: ListView.Selected):
        item = event.item
        if item:
            label = str(item.children[0].renderable) if item.children else ""
            session_id = label.split("]")[0].lstrip("[").strip()
            self._on_select(session_id)
        self.dismiss()

    def on_key(self, event: events.Key):
        if event.key == "escape":
            self.dismiss()


class CodingAgentApp(App):
    """Main TUI application for the coding agent."""

    CSS = """
    #chat-view {
        height: 1fr;
        border: none;
        padding: 0 1;
        margin: 0;
    }

    #input-container {
        dock: bottom;
        height: 3;
        margin: 0 1;
    }

    #suggestion-box {
        dock: bottom;
        height: auto;
        max-height: 10;
        display: none;
        background: $panel;
        border: solid $border;
        margin: 0 2;
        overflow-y: auto;
    }

    #permission-dialog {
        width: 50;
        height: auto;
        padding: 2;
        border: solid $primary;
        background: $surface;
        margin: 5 10;
    }
    .permission-title {
        text-style: bold;
        width: 100%;
        text-align: center;
        padding-bottom: 1;
    }
    .permission-tool {
        color: $accent;
        width: 100%;
    }
    .permission-args {
        color: $text-muted;
        width: 100%;
        padding-bottom: 1;
    }
    .permission-buttons {
        width: 100%;
        height: auto;
        align: center middle;
    }

    #help-container {
        width: 50;
        height: auto;
        padding: 2;
        border: solid $border;
        background: $surface;
        margin: 1 5;
    }
    .help-title {
        text-style: bold;
        width: 100%;
        text-align: center;
        padding-bottom: 1;
    }
    .help-section {
        text-style: bold underline;
        padding-top: 1;
        color: $accent;
    }
    .help-hint {
        text-style: italic;
        color: $text-muted;
        padding-top: 1;
    }

    #session-list-container {
        width: 50;
        height: auto;
        padding: 1;
        border: solid $border;
        background: $surface;
        margin: 5 10;
    }
    .session-list-title {
        text-style: bold;
        width: 100%;
        text-align: center;
        padding-bottom: 1;
    }
    """

    theme_name = reactive(DEFAULT_THEME)
    current_agent = reactive("build")
    is_plan_mode = reactive(False)

    BINDINGS = [
        ("ctrl+x, n", "new_session", "New Session"),
        ("ctrl+x, l", "list_sessions", "List Sessions"),
        ("tab", "switch_agent", "Switch Agent"),
        ("ctrl+x, u", "undo", "Undo"),
        ("ctrl+x, r", "redo", "Redo"),
        ("ctrl+x, t", "toggle_theme", "Theme"),
        ("ctrl+x, d", "toggle_details", "Details"),
        ("ctrl+x, p", "command_palette", "Palette"),
        ("ctrl+x, e", "open_editor", "Editor"),
        ("ctrl+x, x", "export", "Export"),
        ("ctrl+x, q", "exit", "Exit"),
        ("ctrl+x, m", "models", "Models"),
        ("f1", "help", "Help"),
    ]

    def __init__(
        self,
        theme_name: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._input_handler: Optional[Callable] = None
        self._integration = None
        self._chat_view: Optional[ChatView] = None
        self._input_bar: Optional[InputBar] = None
        self._status_bar: Optional[StatusBar] = None
        self._suggestion_box: Optional[Container] = None
        self._show_details = True

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        self._chat_view = ChatView(theme_name=self.theme_name, id="chat-view")
        yield self._chat_view

        self._suggestion_box = Container(id="suggestion-box")
        yield self._suggestion_box

        self._input_bar = InputBar(
            on_submit=self._on_input_submit,
            on_file_ref=self._on_file_ref,
            on_suggestions=self._on_suggestions,
            on_bash_command=self._on_bash_command,
            id="input-container",
        )
        yield self._input_bar

        self._status_bar = StatusBar(id="status-bar")
        yield self._status_bar

        yield Footer()

    def on_mount(self):
        if self._input_bar:
            self._input_bar.focus_input()
        if self._status_bar:
            self._status_bar.agent_name = self.current_agent
            self._status_bar.is_plan_mode = self.is_plan_mode
        model_name = self._get_model_name()
        if self._status_bar:
            self._status_bar.model_name = model_name

    def _get_model_name(self) -> str:
        if self._integration and hasattr(self._integration, 'config'):
            cfg = self._integration.config
            agent_cfg = cfg.agents.get(self.current_agent, None)
            if agent_cfg and agent_cfg.model:
                return agent_cfg.model
            return cfg.model or "default"
        return "default"

    def set_input_handler(self, handler: Callable):
        self._input_handler = handler

    def set_integration(self, integration):
        self._integration = integration

    def _on_input_submit(self, message_value: str):
        if not message_value or not message_value.strip():
            return
        if message_value.startswith("/") and len(message_value) > 1:
            self._handle_slash_command(message_value)
            return
        if self._input_handler:
            import asyncio
            asyncio.create_task(self._input_handler(message_value))

    def _handle_slash_command(self, cmd: str):
        parts = cmd.strip().split()
        command = parts[0].lower()

        if command == "/help":
            self.action_help()
        elif command == "/new":
            self.action_new_session()
        elif command == "/list":
            self.action_list_sessions()
        elif command == "/clear":
            self.clear_chat()
            self.add_user_message("[Chat cleared]")
        elif command == "/undo":
            self.action_undo()
        elif command == "/redo":
            self.action_redo()
        elif command == "/export":
            self.action_export()
        elif command == "/exit" or command == "/quit":
            self.action_exit()
        elif command == "/switch":
            if len(parts) > 1:
                self._switch_to_agent(parts[1])
            else:
                self.add_error("Usage: /switch <agent_name>")
        elif command == "/compact":
            if self._integration:
                self._integration.compact_session()
                self.add_user_message("[Session compacted]")
        elif command == "/models":
            self.action_models()
        else:
            self.add_error(f"Unknown command: {command}")

    def _on_file_ref(self, filepath: str):
        pass

    def _on_bash_command(self, command: str):
        if self._integration:
            import asyncio
            asyncio.create_task(self._integration.handle_bash_command(command))
        else:
            self.add_user_message(f"!{command}")
            self.add_error("Bash command execution not available")

    async def _on_suggestions(self, suggestions: List[str]):
        self.update_suggestions(suggestions)

    # ------------------------------------------------------------------ #
    #  Streaming UI helpers (called from integration thread)              #
    # ------------------------------------------------------------------ #

    def add_user_message(self, message: str):
        if self._chat_view:
            self._chat_view.add_user_message(message)

    def add_agent_message(self, message: str, agent_name: str = "Agent"):
        if self._chat_view:
            self._chat_view.add_agent_message(message, agent_name)

    def add_tool_call(self, name: str, params: str = ""):
        if not self._show_details:
            return
        if self._chat_view:
            self._chat_view.add_tool_call(name, params)

    def update_tool_result(self, name: str, result: str, success: bool = True):
        if not self._show_details:
            return
        if self._chat_view:
            self._chat_view.update_tool_result(name, result, success)

    def set_processing(self, processing: bool):
        if self._status_bar:
            self._status_bar.is_processing = processing

    def add_thinking(self, content: str):
        if not self._show_details:
            return
        if self._chat_view:
            self._chat_view.add_thinking(content)

    def add_error(self, message: str):
        if self._chat_view:
            self._chat_view.add_error(message)

    def add_separator(self):
        if self._chat_view:
            self._chat_view.add_separator()

    def clear_chat(self):
        if self._chat_view:
            self._chat_view.clear()

    def update_suggestions(self, suggestions: List[str], selected: int = 0):
        if not self._suggestion_box:
            return
        self._suggestion_box.remove_children()
        if not suggestions:
            self._suggestion_box.display = False
            return
        for idx, sugg in enumerate(suggestions):
            style = "suggestion-item selected" if idx == selected else "suggestion-item"
            label = Label(sugg, classes=style)
            self._suggestion_box.mount(label)
        self._suggestion_box.display = True

    def _switch_to_agent(self, agent_name: str):
        if self._integration:
            old_name = self.current_agent
            self._integration.switch_agent(agent_name)
            self.current_agent = agent_name
            agent_cfg = self._integration.config.agents.get(agent_name)
            self.is_plan_mode = bool(agent_cfg and agent_cfg.name == "plan" and self._integration.plan_mode)
            if self._status_bar:
                self._status_bar.agent_name = agent_name
                self._status_bar.is_plan_mode = self.is_plan_mode
                self._status_bar.model_name = self._get_model_name()
            if agent_name != old_name:
                self.add_user_message(f"[Switched to {agent_name} agent]")
                self.add_separator()

    async def _show_permission_dialog(self, tool_name: str, args_str: str) -> tuple[bool, bool]:
        """Show permission dialog and return (approved, deny_always)."""
        result = [True, False]
        def on_result(approved: bool, deny_always: bool):
            result[0] = approved
            result[1] = deny_always
        screen = PermissionScreen(tool_name, args_str, on_result)
        await self.push_screen_wait(screen)
        return result[0], result[1]

    def action_new_session(self):
        if self._integration:
            self._integration.new_session()
            self.clear_chat()
            self.add_user_message("[New session started]")
            self.add_separator()
            if self._input_bar:
                self._input_bar.clear()

    def action_list_sessions(self):
        if self._integration:
            sessions = self._integration.list_sessions()
            session_dicts = []
            for s in sessions:
                session_dicts.append({
                    "id": s.id,
                    "agent_name": s.agent_name,
                    "message_count": s.message_count(),
                    "updated_at": s.updated_at,
                })
            screen = SessionListScreen(session_dicts, self._load_session)
            self.push_screen(screen)

    def _load_session(self, session_id: str):
        if self._integration:
            session = self._integration.load_session(session_id)
            if session:
                self.clear_chat()
                self.add_user_message(f"[Loaded session: {session_id[:8]}]")
                self.current_agent = session.agent_name
                if self._status_bar:
                    self._status_bar.agent_name = session.agent_name
                self.add_separator()

    def action_switch_agent(self):
        agents = ["build", "plan"]
        if self.current_agent not in agents:
            self._switch_to_agent("build")
            return
        idx = agents.index(self.current_agent)
        next_agent = agents[(idx + 1) % len(agents)]
        self._switch_to_agent(next_agent)

    def action_undo(self):
        if self._integration:
            success = self._integration.undo()
            if success:
                self.add_user_message("[Undo] Last change reverted")
            else:
                self.add_error("Nothing to undo")
            self.add_separator()

    def action_redo(self):
        if self._integration:
            success = self._integration.redo()
            if success:
                self.add_user_message("[Redo] Change reapplied")
            else:
                self.add_error("Nothing to redo")
            self.add_separator()

    def action_toggle_theme(self):
        theme_names = list(THEMES.keys())
        current_idx = theme_names.index(self.theme_name) if self.theme_name in theme_names else 0
        next_idx = (current_idx + 1) % len(theme_names)
        self.theme_name = theme_names[next_idx]

        theme = get_theme(self.theme_name)
        self.dark = theme.name != "light"

        if self._chat_view:
            self._chat_view.update_theme(self.theme_name)
        if self._status_bar:
            self._status_bar.theme_name = self.theme_name

    def action_toggle_details(self):
        self._show_details = not self._show_details
        status = "shown" if self._show_details else "hidden"
        self.add_user_message(f"[Tool details {status}]")

    def action_command_palette(self):
        self.add_user_message("[Command Palette] Type / to see available commands")
        self.add_error("Use /help for available commands")
        if self._input_bar:
            self._input_bar.set_value("/")

    def action_open_editor(self):
        """Open external editor for multi-line input."""
        try:
            editor = os.environ.get("EDITOR", "vim")
            with tempfile.NamedTemporaryFile(suffix=".md", mode="w+", delete=False) as f:
                f.write("# Enter your message\n")
                f.flush()
                fname = f.name
            subprocess.run([editor, fname], check=True)
            with open(fname, "r", encoding="utf-8") as f:
                content = f.read().strip()
            os.unlink(fname)
            if content and not content.startswith("# Enter your message"):
                self._on_input_submit(content)
            else:
                self.add_error("Editor closed without input")
        except Exception as e:
            self.add_error(f"Editor error: {e}")

    def action_export(self):
        if self._integration:
            result = self._integration.export_session()
            if result:
                self.add_user_message(f"[Exported to {result}]")
            else:
                self.add_error("Export failed")
            self.add_separator()

    def action_models(self):
        model_name = self._get_model_name()
        provider = self._integration.config.provider if self._integration else "azure"
        self.add_user_message(f"[Model: {model_name} | Provider: {provider}]")
        self.add_separator()

    def action_help(self):
        self.push_screen(HelpScreen())

    def action_exit(self):
        self.exit()


async def run_tui(theme_name: Optional[str] = None):
    app = CodingAgentApp(theme_name=theme_name or DEFAULT_THEME)
    await app.run_async()
