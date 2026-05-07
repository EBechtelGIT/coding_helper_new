"""Status bar widget showing agent mode, model, and permissions."""

from textual.widgets import Label, Static
from textual.widget import Widget
from textual.containers import Container, Horizontal
from textual.reactive import reactive
from typing import Optional


class StatusBar(Widget):
    """Status bar showing current agent, mode, model, and theme."""

    agent_name = reactive("build")
    model_name = reactive("default")
    theme_name = reactive("opencode")
    is_plan_mode = reactive(False)

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        padding: 0 1;
        background: $surface;
    }
    #status-agent {
        width: auto;
    }
    #status-mode {
        width: auto;
        margin: 0 1;
    }
    #status-model {
        width: 1fr;
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

    def compose(self):
        with Horizontal(id="status-container"):
            self._agent_label = Label("", id="status-agent")
            yield self._agent_label
            self._mode_label = Label("", id="status-mode")
            yield self._mode_label
            self._model_label = Label("", id="status-model")
            yield self._model_label
            self._theme_label = Label("", id="status-theme")
            yield self._theme_label

    def watch_agent_name(self, value: str):
        if self._agent_label:
            self._agent_label.update(f" {value} ")

    def watch_is_plan_mode(self, value: bool):
        if self._mode_label:
            if value:
                self._mode_label.update("[PLAN MODE]")
                self._mode_label.styles.background = "yellow"
                self._mode_label.styles.color = "black"
            else:
                self._mode_label.update("[BUILD MODE]")
                self._mode_label.styles.background = "green"
                self._mode_label.styles.color = "black"

    def watch_model_name(self, value: str):
        if self._model_label:
            self._model_label.update(f"Model: {value}")

    def watch_theme_name(self, value: str):
        if self._theme_label:
            self._theme_label.update(f"Theme: {value}")

    def update_status(
        self,
        agent: Optional[str] = None,
        model: Optional[str] = None,
        theme: Optional[str] = None,
        is_plan: Optional[bool] = None,
    ):
        if agent is not None:
            self.agent_name = agent
        if model is not None:
            self.model_name = model
        if theme is not None:
            self.theme_name = theme
        if is_plan is not None:
            self.is_plan_mode = is_plan