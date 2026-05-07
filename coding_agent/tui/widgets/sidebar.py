"""Sidebar widget for sessions and agents."""

from textual.widgets import ListView, ListItem, Label
from textual.widget import Widget
from textual.containers import Container, Vertical
from textual.reactive import reactive
from typing import List, Dict, Any, Optional


class SessionItem(ListItem):
    """A session item in the sidebar."""

    def __init__(self, session_id: str, agent_name: str, message_count: int, **kwargs):
        super().__init__(**kwargs)
        self.session_id = session_id
        self.agent_name = agent_name
        self.message_count = message_count

    def compose(self):
        """Render the session item."""
        label = Label(
            f"[{self.session_id[:8]}] {self.agent_name} ({self.message_count} msgs)",
            id=f"session-{self.session_id}",
        )
        yield label


class AgentItem(ListItem):
    """An agent item in the sidebar."""

    def __init__(self, name: str, description: str, is_active: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.agent_name = name
        self.description = description
        self.is_active = is_active

    def compose(self):
        """Render the agent item."""
        marker = ">" if self.is_active else " "
        label = Label(
            f"{marker} {self.agent_name}: {self.description}",
            id=f"agent-{self.agent_name}",
        )
        yield label


class Sidebar(Widget):
    """Sidebar showing sessions and agents."""

    show_sidebar = reactive(True)
    active_agent = reactive("build")
    sessions: reactive[List[Dict[str, Any]]] = reactive([])
    agents: reactive[List[Dict[str, Any]]] = reactive([])

    def __init__(
        self,
        on_session_select: Optional[callable] = None,
        on_agent_select: Optional[callable] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._session_list: Optional[ListView] = None
        self._agent_list: Optional[ListView] = None
        self._on_session_select = on_session_select
        self._on_agent_select = on_agent_select

    def compose(self):
        """Compose the sidebar with session and agent lists."""
        with Vertical(id="sidebar-container"):
            yield Label("=== Sessions ===", classes="sidebar-header")
            self._session_list = ListView(id="session-list")
            yield self._session_list

            yield Label("=== Agents ===", classes="sidebar-header")
            self._agent_list = ListView(id="agent-list")
            yield self._agent_list

    def update_sessions(self, sessions: List[Dict[str, Any]]):
        """Update the session list."""
        self.sessions = sessions
        if self._session_list:
            self._session_list.clear()
            for session in sessions:
                item = SessionItem(
                    session_id=session["id"],
                    agent_name=session["agent_name"],
                    message_count=session.get("message_count", 0),
                )
                self._session_list.append(item)

    def update_agents(self, agents: List[Dict[str, Any]], active: str = "build"):
        """Update the agent list."""
        self.agents = agents
        self.active_agent = active
        if self._agent_list:
            self._agent_list.clear()
            for agent in agents:
                item = AgentItem(
                    name=agent["name"],
                    description=agent.get("description", ""),
                    is_active=(agent["name"] == active),
                )
                self._agent_list.append(item)

    def toggle(self):
        """Toggle sidebar visibility."""
        self.show_sidebar = not self.show_sidebar
        if self.show_sidebar:
            self.styles.display = "block"
        else:
            self.styles.display = "none"

    def _on_list_view_selected(self, message: ListView.Selected):
        """Handle selection in either list."""
        if isinstance(message.item, SessionItem):
            if self._on_session_select:
                self._on_session_select(message.item.session_id)
        elif isinstance(message.item, AgentItem):
            if self._on_agent_select:
                self._on_agent_select(message.item.agent_name)
