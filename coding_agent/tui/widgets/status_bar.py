"""Status bar widget showing agent, mode, model, provider, session, and processing state."""

from textual.widgets import Label
from textual.widget import Widget
from textual.containers import Horizontal
from textual.reactive import reactive
from typing import Optional


SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

AGENT_COLORS = {
    "build": "green",
    "plan": "blue",
    "general": "magenta",
    "explore": "cyan",
}


class StatusBar(Widget):
    """Status bar showing agent, mode, model, provider, session, and processing state."""

    agent_name = reactive("build")
    model_name = reactive("default")
    provider_name = reactive("azure")
    theme_name = reactive("opencode")
    session_id = reactive("")
    parent_session_id = reactive("")
    is_plan_mode = reactive(False)
    is_processing = reactive(False)

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        padding: 0 1;
        background: $surface;
        layout: horizontal;
    }
    #status-agent {
        width: auto;
        padding: 0 1;
    }
    #status-mode {
        width: auto;
        margin: 0 1;
    }
    #status-processing {
        width: auto;
        margin: 0 1;
    }
    #status-model {
        width: 1fr;
    }
    #status-session {
        width: auto;
        text-align: right;
        margin: 0 1;
    }
    #status-parent {
        width: auto;
        text-align: right;
        margin: 0 1;
    }
    #status-theme {
        width: auto;
        text-align: right;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._agent_label: Optional[Label] = None
        self._mode_label: Optional[Label] = None
        self._model_label: Optional[Label] = None
        self._theme_label: Optional[Label] = None
        self._session_label: Optional[Label] = None
        self._parent_label: Optional[Label] = None
        self._processing_label: Optional[Label] = None
        self._spinner_index = 0
        self._spinner_timer = None

    def compose(self):
        with Horizontal(id="status-container"):
            self._agent_label = Label("", id="status-agent")
            yield self._agent_label
            self._mode_label = Label("", id="status-mode")
            yield self._mode_label
            self._processing_label = Label("", id="status-processing")
            yield self._processing_label
            self._model_label = Label("", id="status-model")
            yield self._model_label
            self._session_label = Label("", id="status-session")
            yield self._session_label
            self._parent_label = Label("", id="status-parent")
            yield self._parent_label
            self._theme_label = Label("", id="status-theme")
            yield self._theme_label

    def watch_agent_name(self, value: str):
        if self._agent_label:
            color = AGENT_COLORS.get(value, "green")
            self._agent_label.update(f"[bold {color}]{value}[/bold {color}]")

    def watch_is_plan_mode(self, value: bool):
        if self._mode_label:
            if value:
                self._mode_label.update("[bold yellow]PLAN[/bold yellow]")
                self._mode_label.styles.background = "yellow"
                self._mode_label.styles.color = "black"
            else:
                self._mode_label.update("[bold green]BUILD[/bold green]")
                self._mode_label.styles.background = "green"
                self._mode_label.styles.color = "black"

    def watch_is_processing(self, value: bool):
        if not self._processing_label:
            return
        if value:
            self._spinner_index = 0
            self._advance_spinner()
            self._spinner_timer = self.set_interval(0.12, self._advance_spinner)
        else:
            if self._spinner_timer:
                self._spinner_timer.stop()
                self._spinner_timer = None
            self._processing_label.update("")

    def _advance_spinner(self):
        if not self._processing_label:
            return
        frame = SPINNER_FRAMES[self._spinner_index % len(SPINNER_FRAMES)]
        self._processing_label.update(f" {frame}")
        self._spinner_index += 1

    def watch_model_name(self, value: str):
        if self._model_label:
            self._model_label.update(f"[dim]{value}[/dim]")

    def watch_provider_name(self, value: str):
        if self._session_label:
            pass

    def watch_session_id(self, value: str):
        if self._session_label:
            short_id = value[:8] if value else ""
            self._session_label.update(f"[dim]#{short_id}[/dim]")

    def watch_parent_session_id(self, value: str):
        if self._parent_label:
            if value:
                short_pid = value[:8]
                self._parent_label.update(f"[dim]parent:{short_pid}[/dim]")
            else:
                self._parent_label.update("")

    def watch_theme_name(self, value: str):
        if self._theme_label:
            self._theme_label.update(f"[dim]{value}[/dim]")

    def update_status(
        self,
        agent: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        theme: Optional[str] = None,
        is_plan: Optional[bool] = None,
        session_id: Optional[str] = None,
    ):
        if agent is not None:
            self.agent_name = agent
        if model is not None:
            self.model_name = model
        if provider is not None:
            self.provider_name = provider
        if theme is not None:
            self.theme_name = theme
        if is_plan is not None:
            self.is_plan_mode = is_plan
        if session_id is not None:
            self.session_id = session_id
