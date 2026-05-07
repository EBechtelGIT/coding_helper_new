"""Status bar widget showing agent mode, model, and permissions."""

from textual.widgets import Label, Static
from textual.widget import Widget
from textual.containers import Container, Horizontal
from textual.reactive import reactive
from typing import Optional


class StatusBar(Widget):
    """Status bar showing current agent, model, and mode."""

    agent_name = reactive("build")
    model_name = reactive("default")
    permission_mode = reactive("allow")
    theme_name = reactive("opencode")
    is_plan_mode = reactive(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._agent_label: Optional[Label] = None
        self._model_label: Optional[Label] = None
        self._mode_label: Optional[Label] = None
        self._theme_label: Optional[Label] = None

    def compose(self):
        """Compose the status bar."""
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
        """Update agent display."""
        if self._agent_label:
            mode = " (PLAN)" if self.is_plan_mode else ""
            self._agent_label.update(f"Agent: {value}{mode}")

    def watch_is_plan_mode(self, value: bool):
        """Update plan mode indicator."""
        if self._mode_label:
            if value:
                self._mode_label.update("[PLAN MODE]")
                self._mode_label.styles.color = "yellow"
            else:
                self._mode_label.update("")
                self._mode_label.styles.color = "white"

    def watch_model_name(self, value: str):
        """Update model display."""
        if self._model_label:
            self._model_label.update(f"Model: {value}")

    def watch_theme_name(self, value: str):
        """Update theme display."""
        if self._theme_label:
            self._theme_label.update(f"Theme: {value}")

    def update_status(
        self,
        agent: Optional[str] = None,
        model: Optional[str] = None,
        permission: Optional[str] = None,
        theme: Optional[str] = None,
        is_plan: Optional[bool] = None,
    ):
        """Update multiple status fields at once."""
        if agent is not None:
            self.agent_name = agent
        if model is not None:
            self.model_name = model
        if permission is not None:
            self.permission_mode = permission
        if theme is not None:
            self.theme_name = theme
        if is_plan is not None:
            self.is_plan_mode = is_plan
