"""Main TUI application using Textual."""

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Header, Footer, Label
from textual.reactive import reactive
from typing import Optional, Callable, Dict, Any, List
import os

from coding_agent.tui.themes import get_theme, THEMES, DEFAULT_THEME
from coding_agent.tui.widgets.input_bar import InputBar
from coding_agent.tui.widgets.chat_view import ChatView


class CodingAgentApp(App):
    """Main TUI application for the coding agent."""

    CSS = """
    #chat-view {
        height: 1fr;
        border: solid $border;
        padding: 1;
        overflow-y: auto;
    }

    #status-bar {
        height: 3;
        border-top: solid $border;
        padding: 0 1;
    }

    #status-text {
        margin: 0 1;
    }

    #suggestion-box {
        background: $panel;
        border: solid $border;
        max-height: 10;
        padding: 0;
        dock: bottom;
        margin: 0 1;
    }

    .suggestion-item {
        padding: 0 1;
        height: 1;
    }

    .suggestion-item.selected {
        background: $accent;
    }
    """

    # Reactive attributes
    theme_name = reactive(DEFAULT_THEME)
    current_agent = reactive("build")
    is_plan_mode = reactive(False)

    BINDINGS = [
        # Session management
        ("ctrl+x, n", "new_session", "New Session"),
        ("ctrl+x, l", "list_sessions", "List Sessions"),
        ("tab", "switch_agent", "Switch Agent"),
        # Undo/Redo
        ("ctrl+x, u", "undo", "Undo Last Change"),
        ("ctrl+x, r", "redo", "Redo Change"),
        # UI
        ("ctrl+x, t", "toggle_theme", "Toggle Theme"),
        ("ctrl+x, p", "command_palette", "Command Palette"),
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
        self._input_handler = None
        self._integration = None
        self._chat_view = None
        self._input_bar = None
        self._status_label = None
        self._suggestion_box = None
        self._suggestions = []
        self._selected_suggestion = 0

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        yield Header(show_clock=True)

        with Vertical(id="content"):
            # Use ChatView widget
            self._chat_view = ChatView(theme_name=self.theme_name, id="chat-view")
            yield self._chat_view

            self._status_label = Label(
                f"Agent: {self.current_agent} | Theme: {self.theme_name}",
                id="status-text"
            )
            yield Container(self._status_label, id="status-bar")

            # Input bar with file reference and bash command support
            self._input_bar = InputBar(
                on_submit=self._on_input_submit,
                on_file_ref=self._on_file_ref,
                on_suggestions=self._on_suggestions,
                on_bash_command=self._on_bash_command,
            )
            yield self._input_bar

            # Suggestion box (hidden by default)
            self._suggestion_box = Container(id="suggestion-box")
            yield self._suggestion_box

        yield Footer()

    def on_mount(self):
        """Set up the app after mount."""
        if self._input_bar:
            self._input_bar.focus_input()

    def set_input_handler(self, handler):
        """Set the callback for input submission."""
        self._input_handler = handler

    def set_integration(self, integration):
        """Set the AgentTUIIntegration instance."""
        self._integration = integration

    def _on_input_submit(self, message_value: str):
        """Handle input submission from the InputBar."""
        if self._input_handler:
            import asyncio
            asyncio.create_task(self._input_handler(message_value))

    def _on_file_ref(self, filepath: str):
        """Handle file reference selection."""
        pass

    def _on_bash_command(self, command: str):
        """Handle !bash command from input bar."""
        if self._integration:
            import asyncio
            asyncio.create_task(self._integration.handle_bash_command(command))
        else:
            self.add_user_message(f"!{command}")
            self.add_error("Bash command execution not available in TUI mode")

    async def _on_suggestions(self, suggestions: List[str]):
        """Handle suggestions from InputBar."""
        self.update_suggestions(suggestions)

    def add_user_message(self, message: str):
        """Add a user message to the chat."""
        if self._chat_view:
            self._chat_view.add_user_message(message)

    def add_agent_message(self, message: str, agent_name: str = "Agent"):
        """Add an agent message to the chat."""
        if self._chat_view:
            self._chat_view.add_agent_message(message, agent_name)

    def add_tool_call(self, name: str, params: str = ""):
        """Add a tool call indicator to the chat."""
        if self._chat_view:
            self._chat_view.add_tool_call(name, params)

    def add_tool_result(self, result: str, success: bool = True):
        """Add a tool result to the chat."""
        if self._chat_view:
            self._chat_view.add_tool_result(result, success)

    def add_error(self, message: str):
        """Add an error message to the chat."""
        if self._chat_view:
            self._chat_view.add_error(message)

    def add_separator(self):
        """Add a visual separator between turns."""
        if self._chat_view:
            self._chat_view.add_separator()

    def update_suggestions(self, suggestions: List[str], selected: int = 0):
        """Update the suggestion box with file matches."""
        self._suggestions = suggestions
        self._selected_suggestion = selected

        if not self._suggestion_box:
            return

        # Clear existing suggestions
        self._suggestion_box.remove_children()

        if not suggestions:
            self._suggestion_box.display = False
            return

        # Add suggestion items
        for idx, sugg in enumerate(suggestions):
            style = "suggestion-item selected" if idx == selected else "suggestion-item"
            label = Label(sugg, classes=style)
            self._suggestion_box.mount(label)

        self._suggestion_box.display = True

    def action_toggle_theme(self):
        """Cycle through available themes."""
        theme_names = list(THEMES.keys())
        current_idx = theme_names.index(self.theme_name)
        next_idx = (current_idx + 1) % len(theme_names)
        self.theme_name = theme_names[next_idx]

        # Update status bar
        if self._status_label:
            self._status_label.update(
                f"Agent: {self.current_agent} | Theme: {self.theme_name}"
            )

        # Update the UI colors
        theme = get_theme(self.theme_name)
        self.dark = theme.name != "light"

        # Apply theme colors to widgets
        if self._chat_view:
            self._chat_view.update_theme(self.theme_name)
        if self._input_bar:
            self._input_bar.styles.border = f"solid {theme.border}"

    def action_undo(self):
        """Undo last change."""
        if self._integration:
            success = self._integration.undo()
            if success:
                self.add_user_message("[Undo] Last change undone")
            else:
                self.add_error("Nothing to undo")

    def action_redo(self):
        """Redo last undone change."""
        if self._integration:
            success = self._integration.redo()
            if success:
                self.add_user_message("[Redo] Change reapplied")
            else:
                self.add_error("Nothing to redo")

    def action_exit(self):
        """Exit the application."""
        self.exit()

    # Stub methods for missing actions
    def action_new_session(self):
        """Create a new session."""
        self.add_user_message("[New Session] Feature coming soon")

    def action_list_sessions(self):
        """List all sessions."""
        self.add_user_message("[List Sessions] Feature coming soon")

    def action_switch_agent(self):
        """Switch the current agent."""
        self.add_user_message("[Switch Agent] Feature coming soon")

    def action_command_palette(self):
        """Open command palette."""
        self.add_user_message("[Command Palette] Feature coming soon")

    def action_open_editor(self):
        """Open editor."""
        self.add_user_message("[Editor] Feature coming soon")

    def action_export(self):
        """Export conversation."""
        self.add_user_message("[Export] Feature coming soon")

    def action_models(self):
        """Show/models management."""
        self.add_user_message("[Models] Feature coming soon")

    def action_help(self):
        """Show help."""
        self.add_user_message("[Help] Feature coming soon")


async def run_tui(theme_name: Optional[str] = None):
    """Run the TUI application."""
    app = CodingAgentApp(theme_name=theme_name or DEFAULT_THEME)
    await app.run_async()


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_tui())
