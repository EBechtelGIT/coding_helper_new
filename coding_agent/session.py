"""Session management, persistence, and context compaction."""

import json
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
    ToolMessage,
)


SESSIONS_DIR = Path(".coding-agent") / "sessions"


@dataclass
class Session:
    """Represents a single conversation session."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    messages: list = field(default_factory=list)
    agent_name: str = "build"
    parent_id: Optional[str] = None
    child_ids: list = field(default_factory=list)
    compacted_summary: str = ""

    def add_message(self, message: BaseMessage) -> None:
        self.messages.append(_message_to_serializable(message))
        self.updated_at = time.time()

    def add_messages(self, messages: list[BaseMessage]) -> None:
        for msg in messages:
            self.messages.append(_message_to_serializable(msg))
        self.updated_at = time.time()

    def get_messages(self) -> list[BaseMessage]:
        return [_serializable_to_message(m) for m in self.messages]

    def message_count(self) -> int:
        return len(self.messages)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        known_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_keys}
        return cls(**filtered)


def _message_to_serializable(msg: BaseMessage) -> dict:
    if isinstance(msg, HumanMessage):
        return {"type": "human", "content": msg.content}
    elif isinstance(msg, AIMessage):
        return {
            "type": "ai",
            "content": msg.content,
            "tool_calls": getattr(msg, "tool_calls", None) or [],
        }
    elif isinstance(msg, ToolMessage):
        return {
            "type": "tool",
            "content": msg.content,
            "tool_call_id": getattr(msg, "tool_call_id", ""),
            "name": getattr(msg, "name", ""),
        }
    elif isinstance(msg, SystemMessage):
        return {"type": "system", "content": msg.content}
    else:
        return {"type": str(msg.type), "content": msg.content}


def _serializable_to_message(data: dict) -> BaseMessage:
    msg_type = data.get("type", "")
    content = data.get("content", "")

    if msg_type == "human":
        return HumanMessage(content=content)
    elif msg_type == "ai":
        extra = {}
        if data.get("tool_calls"):
            extra["tool_calls"] = data["tool_calls"]
        return AIMessage(content=content, **extra)
    elif msg_type == "tool":
        return ToolMessage(
            content=content,
            tool_call_id=data.get("tool_call_id", ""),
            name=data.get("name", ""),
        )
    elif msg_type == "system":
        return SystemMessage(content=content)
    else:
        return HumanMessage(content=content)


class SessionManager:
    """Manages session persistence and lifecycle."""

    def __init__(self, sessions_dir: Path = SESSIONS_DIR):
        self.sessions_dir = sessions_dir
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, Session] = {}
        self._current_session: Optional[Session] = None
        self._load_all()

    def _load_all(self) -> None:
        for f in self.sessions_dir.glob("*.json"):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                session = Session.from_dict(data)
                self._sessions[session.id] = session
            except (json.JSONDecodeError, KeyError, TypeError):
                continue

    def _save_session(self, session: Session) -> None:
        path = self.sessions_dir / f"{session.id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(session.to_dict(), f, indent=2, default=str)

    def create_session(self, agent_name: str = "build") -> Session:
        session = Session(agent_name=agent_name)
        self._sessions[session.id] = session
        self._current_session = session
        self._save_session(session)
        return session

    def load_session(self, session_id: str) -> Optional[Session]:
        session = self._sessions.get(session_id)
        if session:
            self._current_session = session
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        session = self._sessions.pop(session_id, None)
        if session:
            path = self.sessions_dir / f"{session.id}.json"
            if path.exists():
                path.unlink()
            if self._current_session and self._current_session.id == session_id:
                self._current_session = None
            return True
        return False

    def list_sessions(self) -> list[Session]:
        return sorted(self._sessions.values(), key=lambda s: s.updated_at, reverse=True)

    def save_current(self) -> None:
        if self._current_session:
            self._current_session.updated_at = time.time()
            self._save_session(self._current_session)

    def get_current(self) -> Optional[Session]:
        return self._current_session

    def set_current(self, session: Session) -> None:
        self._current_session = session

    def add_child(self, parent_id: str, child_id: str) -> None:
        parent = self._sessions.get(parent_id)
        if parent and child_id not in parent.child_ids:
            parent.child_ids.append(child_id)
            parent.updated_at = time.time()
            self._save_session(parent)
        child = self._sessions.get(child_id)
        if child:
            child.parent_id = parent_id
            self._save_session(child)


class ContextCompactor:
    """Compacts old messages when context gets too long."""

    def __init__(self, max_messages: int = 50, compact_to: int = 20):
        self.max_messages = max_messages
        self.compact_to = compact_to

    def needs_compaction(self, session: Session) -> bool:
        return session.message_count() > self.max_messages

    def compact(self, session: Session, llm=None) -> list[BaseMessage]:
        messages = session.get_messages()
        if llm and len(messages) > self.max_messages:
            return self._compact_with_llm(messages, llm)
        return self._compact_simple(messages)

    def _compact_with_llm(self, messages: list[BaseMessage], llm) -> list[BaseMessage]:
        old_messages = messages[:-self.compact_to]
        keep_messages = messages[-self.compact_to:]

        conversation_text = "\n".join(
            f"{type(m).__name__}: {m.content}" for m in old_messages if m.content
        )[:4000]

        summary_prompt = (
            "Summarize the following conversation in 3-5 sentences. "
            "Focus on: what the user wants, what has been done, and what remains.\n\n"
            f"Conversation:\n{conversation_text}"
        )

        try:
            response = llm.invoke([HumanMessage(content=summary_prompt)])
            summary = response.content if hasattr(response, "content") else str(response)
        except Exception:
            summary = f"Previous conversation had {len(old_messages)} messages. Key actions were taken."

        system_msg = SystemMessage(
            content=f"[Previous conversation summary]: {summary}"
        )

        return [system_msg] + keep_messages

    def _compact_simple(self, messages: list[BaseMessage]) -> list[BaseMessage]:
        if len(messages) <= self.max_messages:
            return messages

        keep = messages[-self.compact_to:]
        system_msg = SystemMessage(
            content=f"[Conversation was compacted. {len(messages) - self.compact_to} earlier messages removed.]"
        )
        return [system_msg] + keep
