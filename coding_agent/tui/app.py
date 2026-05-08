"""Main TUI application using Textual - OpenCode-inspired design."""

import os
import tempfile
import subprocess
from datetime import datetime
from typing import Optional, Callable, Dict, Any, List

import asyncio

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
from coding_agent.commands import list_custom_commands, ensure_commands_dir


AGENT_COLORS = {
    "build": "green",
    "plan": "blue",
    "general": "magenta",
    "explore": "cyan",
}


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
            Label("  Ctrl+X E    Open editor"),
            Label("  Ctrl+X X    Export conversation"),
            Label("  Ctrl+X M    Show model info"),
            Label("  Ctrl+X C    Compact session"),
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
            Label("  /thinking   Toggle thinking display"),
            Label("  /themes     List/switch themes"),
            Label("  /commands   List custom commands"),
            Label("  /fork       Start a new forked session"),
            Label("  /parent     Navigate to parent session"),
            Label("  /child      Navigate to child session"),
            Label("  /sibling    Navigate to sibling session"),
            Label("  /init       Initialize AGENTS.md"),
            Label("  /exit       Exit"),
            Label("  @file       Reference a file"),
            Label("  !command    Run a command"),
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
            agent = s.get("agent_name", "?")
            color = AGENT_COLORS.get(agent, "green")
            label = f"[{s.get('id', '?')[:8]}] [{color}]{agent}[/{color}]  {s.get('message_count', 0)} msgs"
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


class ThemesScreen(ModalScreen):
    """Modal screen to list and switch themes."""

    def __init__(self, current: str, on_select: Callable[[str], None], **kwargs):
        super().__init__(**kwargs)
        self._current = current
        self._on_select = on_select

    def compose(self):
        yield Container(
            Label("Themes", classes="theme-list-title"),
            id="theme-list-container",
        )

    def on_mount(self):
        container = self.query_one("#theme-list-container")
        lv = ListView(id="theme-list-view")
        for name in THEMES:
            marker = " \u25c6" if name == self._current else "  "
            lv.append(ListItem(Label(f"{marker}{name}")))
        container.mount(lv)

    def on_list_view_selected(self, event: ListView.Selected):
        item = event.item
        if item:
            label = str(item.children[0].renderable) if item.children else ""
            name = label.strip().lstrip("\u25c6").strip()
            if name:
                self._on_select(name)
        self.dismiss()

    def on_key(self, event: events.Key):
        if event.key == "escape":
            self.dismiss()


class QuestionScreen(ModalScreen):
    """Modal screen for the LLM to ask the user questions."""

    def __init__(self, header: str, question: str, options: list, multiple: bool = False, **kwargs):
        super().__init__(**kwargs)
        self._header = header
        self._question = question
        self._options = options
        self._multiple = multiple
        self.result = None

    def compose(self):
        with Container(id="question-dialog"):
            yield Label(self._header, classes="question-header")
            yield Label(self._question, classes="question-text")
            if self._options:
                yield Label("", classes="question-options-label")
                for opt in self._options:
                    yield Button(opt, name="opt", classes="question-option")
            if not self._options:
                from textual.widgets import Input as TInput
                yield TInput(placeholder="Type your answer...", id="question-input")
            yield Button("Submit", variant="primary", id="question-submit", classes="question-submit")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.name == "opt":
            self.result = [event.button.label]
            self.dismiss()
        elif event.button.id == "question-submit":
            if self._options and self._multiple:
                selected = []
                for btn in self.query(".question-option"):
                    if hasattr(btn, 'variant') and btn.variant == "primary":
                        selected.append(btn.label)
                self.result = selected if selected else ["(none selected)"]
            else:
                inp = self.query_one("#question-input")
                val = inp.value.strip() if hasattr(inp, 'value') else ""
                self.result = [val] if val else ["(skipped)"]
            self.dismiss()

    def on_key(self, event: events.Key):
        if event.key == "escape":
            self.result = ["(cancelled)"]
            self.dismiss()


class CodingAgentApp(App):
    """Main TUI application - OpenCode-inspired design."""

    CSS = """
    Screen {
        background: $background;
    }

    #chat-view {
        height: 1fr;
        border: none;
        padding: 0 1;
        margin: 0;
        background: $background;
    }

    #input-container {
        dock: bottom;
        height: 3;
        margin: 0 1;
        background: $surface;
        border: none;
    }

    #suggestion-box {
        dock: bottom;
        height: auto;
        max-height: 10;
        display: none;
        background: $panel;
        border: none;
        margin: 0 2;
        overflow-y: auto;
    }

    #input-field {
        background: $surface;
        border: none;
        color: $text;
    }

    #input-field:focus {
        border: none;
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

    #session-list-container, #theme-list-container {
        width: 40;
        height: auto;
        padding: 1;
        border: solid $border;
        background: $surface;
        margin: 5 10;
    }
    #question-dialog {
        width: 60;
        height: auto;
        padding: 2;
        border: solid $primary;
        background: $surface;
        margin: 3 8;
    }
    .question-header {
        text-style: bold;
        width: 100%;
        text-align: center;
        padding-bottom: 1;
        color: $accent;
    }
    .question-text {
        width: 100%;
        padding-bottom: 1;
    }
    .question-options-label {
        padding-bottom: 1;
    }
    .question-option {
        width: 100%;
        margin: 0 0 1 0;
    }
    .question-submit {
        width: 100%;
        margin-top: 1;
    }

    .session-list-title, .theme-list-title {
        text-style: bold;
        width: 100%;
        text-align: center;
        padding-bottom: 1;
    }

    Header {
        background: $surface;
        color: $text;
        height: 1;
    }

    Footer {
        background: $surface;
        color: $text-muted;
        height: 1;
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
        ("ctrl+x, c", "compact", "Compact"),
        ("ctrl+x, q", "exit", "Exit"),
        ("ctrl+x, m", "models", "Models"),
        ("ctrl+x, [", "nav_parent", "Parent Session"),
        ("ctrl+x, ]", "nav_child", "Child Session"),
        ("ctrl+x, \\", "nav_sibling", "Next Sibling"),
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
        self._show_thinking = True

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
        provider = self._get_provider_name()
        if self._status_bar:
            self._status_bar.provider_name = provider
        if self._status_bar and self._integration:
            session = self._integration.current_session
            if session:
                self._status_bar.session_id = session.id

    def _get_model_name(self) -> str:
        if self._integration and hasattr(self._integration, 'config'):
            cfg = self._integration.config
            agent_cfg = cfg.agents.get(self.current_agent, None)
            if agent_cfg and agent_cfg.model:
                return agent_cfg.model
            return cfg.model or "default"
        return "default"

    def _get_provider_name(self) -> str:
        if self._integration and hasattr(self._integration, 'config'):
            return self._integration.config.provider
        return "azure"

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
            asyncio.create_task(self._input_handler(message_value))

    def _handle_slash_command(self, cmd: str):
        parts = cmd.strip().split()
        command = parts[0].lower()

        if command == "/help":
            self.action_help()
        elif command == "/new":
            self.action_new_session()
        elif command == "/list" or command == "/sessions":
            self.action_list_sessions()
        elif command == "/clear":
            self.clear_chat()
            self.add_system_message("Chat cleared")
        elif command == "/undo":
            self.action_undo()
        elif command == "/redo":
            self.action_redo()
        elif command == "/export" or command == "/share":
            self.action_export()
        elif command == "/exit" or command == "/quit":
            self.action_exit()
        elif command == "/switch":
            if len(parts) > 1:
                self._switch_to_agent(parts[1])
            else:
                self.add_system_message("Usage: /switch <agent_name>")
        elif command == "/compact":
            if self._integration:
                self._integration.compact_session()
                self.add_system_message("Session compacted")
        elif command == "/models":
            self.action_models()
        elif command == "/thinking":
            self._show_thinking = not self._show_thinking
            if self._chat_view:
                self._chat_view.set_show_thinking(self._show_thinking)
            status = "shown" if self._show_thinking else "hidden"
            self.add_system_message(f"Thinking blocks {status}")
        elif command == "/themes" or command == "/theme":
            if len(parts) > 1 and parts[1] in THEMES:
                self._apply_theme(parts[1])
            else:
                self._show_theme_screen()
        elif command == "/commands" or command == "/cmds":
            self._show_custom_commands()
        elif command == "/parent":
            self.action_nav_parent()
        elif command == "/child":
            self.action_nav_child()
        elif command == "/sibling":
            self.action_nav_sibling()
        elif command == "/fork":
            self.action_new_session()
            self.add_system_message("Forked new session")
        elif command == "/init":
            asyncio.create_task(self._run_init())
        else:
            self.add_system_message(f"Unknown command: {command}. Type /help")

    def _show_custom_commands(self):
        cmds = list_custom_commands()
        if not cmds:
            self.add_system_message("No custom commands defined. Create .opencode/commands/<name>.md files")
            return
        lines = [f"/{c}" for c in cmds]
        self.add_system_message("Custom commands: " + ", ".join(lines))

    async def _run_init(self):
        """Run /init to analyze project and generate AGENTS.md."""
        if self._integration and hasattr(self._integration, 'run_init'):
            await self._integration.run_init()
            self.add_system_message("AGENTS.md created/updated")
        else:
            self.add_system_message("/init not available")

    def _on_file_ref(self, filepath: str):
        if self._integration and hasattr(self._integration, 'handle_file_reference'):
            asyncio.create_task(self._integration.handle_file_reference(filepath))

    def _on_bash_command(self, command: str):
        allow = False
        if self._integration and hasattr(self._integration, 'config'):
            allow = getattr(self._integration.config, 'allow_bash', False)
        if not allow:
            self.add_system_message("Bash commands are disabled. Enable with --allow-bash")
            return
        if self._integration:
            asyncio.create_task(self._integration.handle_bash_command(command))
        else:
            self.add_system_message(f"!{command}")
            self.add_system_message("Bash command execution not available")

    async def _on_suggestions(self, suggestions: List[str]):
        self.update_suggestions(suggestions)

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

    def add_system_message(self, message: str):
        if self._chat_view:
            self._chat_view.add_system_message(message)

    def add_plan(self, plan_text: str):
        if self._chat_view:
            self._chat_view.add_plan(plan_text)

    def add_file_injection(self, filepath: str, content_preview: str = ""):
        if self._chat_view:
            self._chat_view.add_file_injection(filepath, content_preview)

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
                self.add_system_message(f"Switched to {agent_name} agent")
                self.add_separator()

    async def _show_permission_dialog(self, tool_name: str, args_str: str) -> tuple[bool, bool]:
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
            self.add_system_message("New session started")
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
                self.add_system_message(f"Loaded session: {session_id[:8]}")
                self.current_agent = session.agent_name
                if self._status_bar:
                    self._status_bar.agent_name = session.agent_name
                    self._status_bar.session_id = session.id
                self.add_separator()

    def action_switch_agent(self):
        primary_agents = ["build", "plan"]
        if self.current_agent not in primary_agents:
            self._switch_to_agent("build")
            return
        idx = primary_agents.index(self.current_agent)
        next_agent = primary_agents[(idx + 1) % len(primary_agents)]
        self._switch_to_agent(next_agent)

    def action_undo(self):
        if self._integration:
            success = self._integration.undo()
            if success:
                self.add_system_message("Undo: Last change reverted")
            else:
                self.add_system_message("Nothing to undo")
            self.add_separator()

    def action_redo(self):
        if self._integration:
            success = self._integration.redo()
            if success:
                self.add_system_message("Redo: Change reapplied")
            else:
                self.add_system_message("Nothing to redo")
            self.add_separator()

    def _apply_theme(self, theme_name: str):
        self.theme_name = theme_name
        theme = get_theme(theme_name)
        self.dark = theme_name != "light"
        if self._chat_view:
            self._chat_view.update_theme(theme_name)
        if self._status_bar:
            self._status_bar.theme_name = theme_name
        self.add_system_message(f"Theme: {theme_name}")

    def action_toggle_theme(self):
        theme_names = list(THEMES.keys())
        current_idx = theme_names.index(self.theme_name) if self.theme_name in theme_names else 0
        next_idx = (current_idx + 1) % len(theme_names)
        self._apply_theme(theme_names[next_idx])

    def _show_theme_screen(self):
        screen = ThemesScreen(self.theme_name, self._apply_theme)
        self.push_screen(screen)

    def action_toggle_details(self):
        self._show_details = not self._show_details
        status = "shown" if self._show_details else "hidden"
        self.add_system_message(f"Tool details {status}")

    def action_command_palette(self):
        self.add_system_message("Command Palette: Type / to see commands")
        if self._input_bar:
            self._input_bar.set_value("/")

    def action_open_editor(self):
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
                self.add_system_message("Editor closed without input")
        except Exception as e:
            self.add_system_message(f"Editor error: {e}")

    def action_export(self):
        if self._integration:
            result = self._integration.export_session()
            if result:
                self.add_system_message(f"Exported to {result}")
            else:
                self.add_system_message("Export failed")
            self.add_separator()

    def action_compact(self):
        if self._integration:
            self._integration.compact_session()
            self.add_system_message("Session compacted")
            self.add_separator()

    def action_models(self):
        model_name = self._get_model_name()
        provider = self._get_provider_name()
        self.add_system_message(f"Model: {model_name} | Provider: {provider}")
        self.add_separator()

    def action_nav_parent(self):
        if self._integration and self._integration.navigate_to_parent():
            self.clear_chat()
            self.add_system_message("Navigated to parent session")
            self.add_separator()
        else:
            self.add_system_message("No parent session")

    def action_nav_child(self):
        if self._integration and self._integration.navigate_to_child():
            self.clear_chat()
            self.add_system_message("Navigated to child session")
            self.add_separator()
        else:
            self.add_system_message("No child session")

    def action_nav_sibling(self):
        if not self._integration:
            return
        siblings = self._integration.list_sibling_sessions()
        if not siblings:
            self.add_system_message("No sibling sessions")
            return
        sib = siblings[0]
        self._integration.load_session(sib.id)
        self.clear_chat()
        self.add_system_message(f"Switched to sibling session {sib.id[:8]}")
        self.add_separator()

    def action_help(self):
        self.push_screen(HelpScreen())

    def action_exit(self):
        self.exit()


async def run_tui(theme_name: Optional[str] = None):
    app = CodingAgentApp(theme_name=theme_name or DEFAULT_THEME)
    await app.run_async()
