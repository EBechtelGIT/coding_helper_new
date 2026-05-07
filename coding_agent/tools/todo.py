"""Todo tracking tool for structured task management."""

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field


class TodoList:
    """Simple in-memory todo list."""

    def __init__(self):
        self._todos: list[dict] = []

    def write(self, todos: list[dict]) -> str:
        """Set the todo list. Each item has 'content' and 'status'."""
        self._todos = []
        for i, item in enumerate(todos, 1):
            self._todos.append({
                "id": i,
                "content": item.get("content", ""),
                "status": item.get("status", "pending"),
            })
        return f"Todo list updated with {len(self._todos)} items."

    def read(self) -> str:
        if not self._todos:
            return "No tasks tracked."

        lines = []
        for item in self._todos:
            status_icon = {
                "pending": " ",
                "in_progress": ">",
                "completed": "x",
                "cancelled": "-",
            }.get(item["status"], " ")
            lines.append(f"- [{status_icon}] {item['content']}")
        return "\n".join(lines)

    def get_todos(self) -> list[dict]:
        return list(self._todos)


_todo_list = TodoList()


class TodoWriteSchema(BaseModel):
    todos: list[dict] = Field(
        description="List of todo items. Each item: {'content': 'task description', 'status': 'pending|in_progress|completed|cancelled'}"
    )


class TodoReadSchema(BaseModel):
    pass


def todowrite_func(todos: list[dict]) -> str:
    """Create or update the todo list. Use this to track progress on complex tasks."""
    return _todo_list.write(todos)


def todoread_func() -> str:
    """Read the current todo list."""
    return _todo_list.read()


def get_todo_tools() -> list[StructuredTool]:
    return [
        StructuredTool.from_function(
            func=todowrite_func,
            name="todowrite",
            description="Create or update a structured todo list. Use to track multi-step tasks with items that have content and status (pending, in_progress, completed, cancelled).",
            args_schema=TodoWriteSchema,
        ),
        StructuredTool.from_function(
            func=todoread_func,
            name="todoread",
            description="Read the current todo list to check task progress.",
            args_schema=TodoReadSchema,
        ),
    ]
