"""Enhanced input bar with @ file references and ! bash commands."""

from textual.widgets import Input
from textual.widget import Widget
from textual.containers import Container
from textual.reactive import reactive
from textual.message import Message
from textual import events
import os
import re
from typing import Optional, List, Callable


class FileSuggestion(Message):
    """Message sent when file suggestions are available."""
    def __init__(self, suggestions: List[str]):
        super().__init__()
        self.suggestions = suggestions


class InputBar(Widget):
    """Input bar with support for @ file references and ! bash commands."""

    show_suggestions = reactive(False)
    suggestions: reactive[List[str]] = reactive([])
    selected_suggestion = reactive(0)
    input_value = reactive("")

    def __init__(
        self,
        on_submit: Optional[Callable] = None,
        on_file_ref: Optional[Callable] = None,
        on_suggestions: Optional[Callable] = None,
        on_bash_command: Optional[Callable] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._input: Optional[Input] = None
        self._on_submit = on_submit
        self._on_file_ref = on_file_ref
        self._on_suggestions = on_suggestions
        self._on_bash_command = on_bash_command
        self._workdir = os.getcwd()

    def compose(self):
        with Container():
            self._input = Input(
                placeholder="Type a message... (@ for files, ! for commands, / for commands)",
                id="input-field",
            )
            yield self._input

    def on_mount(self):
        if self._input:
            self._input.focus()

    def on_key(self, event: events.Key) -> None:
        if not self.show_suggestions or not self.suggestions:
            return

        if event.key == "down":
            self.selected_suggestion = (self.selected_suggestion + 1) % len(self.suggestions)
            self.refresh()
            event.stop()
        elif event.key == "up":
            self.selected_suggestion = (self.selected_suggestion - 1) % len(self.suggestions)
            self.refresh()
            event.stop()
        elif event.key == "enter":
            if self.suggestions:
                selected = self.suggestions[self.selected_suggestion]
                self._insert_file_ref(selected)
                event.stop()

    async def _insert_file_ref(self, filepath: str):
        if self._input:
            current = self._input.value
            new_value = re.sub(r'@\S*$', f'@{filepath} ', current)
            self._input.value = new_value
            self.show_suggestions = False
            self.suggestions = []
            self._input.focus()

    def on_input_changed(self, message: Input.Changed) -> None:
        value = message.value
        self.input_value = value

        if self._check_for_bash_command(value):
            return

        self._check_for_file_ref(value)

    def on_input_submitted(self, message: Input.Submitted) -> None:
        if self._on_submit:
            self._on_submit(message.value)
        if self._input:
            self._input.value = ""
        self.show_suggestions = False
        self.suggestions = []

    def _check_for_bash_command(self, value: str):
        if value.startswith('!'):
            cmd = value[1:].strip()
            if cmd and self._on_bash_command:
                self._on_bash_command(cmd)
            return True
        return False

    def _check_for_file_ref(self, value: str):
        match = re.search(r'@(\S*)$', value)
        if match and not value.startswith('!'):
            partial = match.group(1)
            self._show_file_suggestions(partial)
        else:
            self.show_suggestions = False
            self.suggestions = []

    def _show_file_suggestions(self, partial: str):
        pattern = f"**/*{partial}*" if partial else "**/*"

        matches = []
        for root, dirs, files in os.walk(self._workdir):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {'node_modules', '__pycache__', 'venv', '.git', '.venv'}]

            for file in files:
                if file.startswith('.'):
                    continue
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, self._workdir)

                if not partial or partial.lower() in rel_path.lower():
                    matches.append(rel_path)
                    if len(matches) >= 10:
                        break

            if len(matches) >= 10:
                break

        self.suggestions = sorted(matches)
        self.selected_suggestion = 0
        self.show_suggestions = bool(matches)

        if self._on_suggestions:
            self._on_suggestions(matches)

    def set_value(self, value: str):
        if self._input:
            self._input.value = value
            self._input.cursor_position = len(value)
            self._input.focus()

    def clear(self):
        if self._input:
            self._input.value = ""

    def focus_input(self):
        if self._input:
            self._input.focus()

    def get_value(self) -> str:
        return self._input.value if self._input else ""
