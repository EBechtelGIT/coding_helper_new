"""Enhanced input bar with @ file references and ! bash commands."""

from textual.widgets import Input
from textual.widget import Widget
from textual.containers import Container, Vertical
from textual.reactive import reactive
from textual.message import Message
from textual import events
import os
import re
import glob
from typing import Optional, List, Callable


class FileSuggestion(Message):
    """Message sent when file suggestions are available."""
    def __init__(self, suggestions: List[str]):
        super().__init__()
        self.suggestions = suggestions


class InputBar(Widget):
    """Input bar with support for @ file references and ! bash commands."""

    # Reactive attributes for UI state
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
        """Compose the input bar with suggestions dropdown."""
        with Container():
            self._input = Input(
                placeholder="Type a message... (use @ for files, ! for bash)",
                id="input-field",
            )
            yield self._input
            # Suggestions will be rendered by parent

    def on_mount(self):
        """Set up event handlers."""
        if self._input:
            self._input.focus()

    def on_key(self, event: events.Key) -> None:
        """Handle key events for navigation."""
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
        """Insert a file reference into the input."""
        if self._input:
            current = self._input.value
            # Replace the @partial with the full path
            new_value = re.sub(r'@\S*$', f'@{filepath} ', current)
            self._input.value = new_value
            self.show_suggestions = False
            self.suggestions = []
            self._input.focus()

    def on_input_changed(self, message: Input.Changed) -> None:
        """Handle input changes to detect @ and ! prefixes."""
        value = message.value
        self.input_value = value

        # Check for !bash command first
        if self._check_for_bash_command(value):
            return

        # Check for @file reference
        self._check_for_file_ref(value)

    def on_input_submitted(self, message: Input.Submitted) -> None:
        """Handle input submission."""
        if self._on_submit:
            self._on_submit(message.value)
        if self._input:
            self._input.value = ""
        self.show_suggestions = False
        self.suggestions = []

    def _check_for_bash_command(self, value: str):
        """Check if user is typing a bash command (!)."""
        # Match !command at start of input
        if value.startswith('!'):
            # Extract command after !
            cmd = value[1:].strip()
            if cmd and self._on_bash_command:
                self._on_bash_command(cmd)
            return True
        return False

    def _check_for_file_ref(self, value: str):
        """Check if user is typing a file reference (@)."""
        # Check if we're in the middle of typing an @ reference
        # Match @pattern at end of input (before cursor)
        match = re.search(r'@(\S*)$', value)
        if match and not value.startswith('!'):
            partial = match.group(1)
            self._show_file_suggestions(partial)
        else:
            self.show_suggestions = False
            self.suggestions = []

    def _show_file_suggestions(self, partial: str):
        """Show file suggestions based on partial input."""
        # Use glob for fuzzy-like search
        pattern = f"**/*{partial}*" if partial else "**/*"
        
        matches = []
        for root, dirs, files in os.walk(self._workdir):
            # Skip hidden dirs and common non-code dirs
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {'node_modules', '__pycache__', 'venv', '.git'}]
            
            for file in files:
                if file.startswith('.'):
                    continue
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, self._workdir)
                
                # Check if partial matches any part of the path
                if not partial or partial.lower() in rel_path.lower():
                    matches.append(rel_path)
                    if len(matches) >= 10:  # Limit to 10 suggestions
                        break
            
            if len(matches) >= 10:
                break

        self.suggestions = sorted(matches)
        self.selected_suggestion = 0
        self.show_suggestions = bool(matches)
        
        # Notify parent about suggestions
        if self._on_suggestions:
            self._on_suggestions(matches)

    def _is_hidden_or_binary(self, filepath: str) -> bool:
        """Check if a file should be excluded from suggestions."""
        name = os.path.basename(filepath)
        if name.startswith('.'):
            return True
        binary_exts = {'.pyc', '.o', '.so', '.dylib', '.exe', '.bin', '.png', '.jpg', '.gif', '.pdf'}
        ext = os.path.splitext(filepath)[1].lower()
        return ext in binary_exts

    def set_value(self, value: str):
        """Set the input field value."""
        if self._input:
            self._input.value = value
            self._input.cursor_position = len(value)
            self._input.focus()

    def clear(self):
        """Clear the input field."""
        if self._input:
            self._input.value = ""

    def focus_input(self):
        """Focus the input field."""
        if self._input:
            self._input.focus()

    def get_value(self) -> str:
        """Get the current input value."""
        return self._input.value if self._input else ""
