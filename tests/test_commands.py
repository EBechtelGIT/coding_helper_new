"""Tests for the custom commands system."""

import tempfile
from pathlib import Path

from coding_agent.commands import (
    list_custom_commands,
    get_custom_command,
    _parse_frontmatter,
)


def test_parse_frontmatter_simple():
    text = "---\nkey: value\n---\nBody text"
    result = _parse_frontmatter(text)
    assert result == {"key": "value"}


def test_parse_frontmatter_no_frontmatter():
    assert _parse_frontmatter("No frontmatter here") is None


def test_parse_frontmatter_incomplete():
    assert _parse_frontmatter("---\nkey: value") is None


def test_list_custom_commands(tmp_path):
    cmd_dir = tmp_path / ".opencode" / "commands"
    cmd_dir.mkdir(parents=True)
    (cmd_dir / "fix.md").write_text("fix prompt")
    (cmd_dir / "test.md").write_text("test prompt")

    import coding_agent.commands as cmds
    original_dir = cmds.COMMANDS_DIR
    try:
        cmds.COMMANDS_DIR = cmd_dir
        result = list_custom_commands()
        assert "fix" in result
        assert "test" in result
    finally:
        cmds.COMMANDS_DIR = original_dir


def test_get_custom_command(tmp_path):
    cmd_dir = tmp_path / ".opencode" / "commands"
    cmd_dir.mkdir(parents=True)
    (cmd_dir / "review.md").write_text("Review this: {{input}}")

    import coding_agent.commands as cmds
    original_dir = cmds.COMMANDS_DIR
    try:
        cmds.COMMANDS_DIR = cmd_dir
        prompt = get_custom_command("review")
        assert prompt == "Review this: {{input}}"

        assert get_custom_command("nonexistent") is None
    finally:
        cmds.COMMANDS_DIR = original_dir


def test_get_custom_command_with_frontmatter(tmp_path):
    cmd_dir = tmp_path / ".opencode" / "commands"
    cmd_dir.mkdir(parents=True)
    (cmd_dir / "ask.md").write_text("---\nprompt: Answer the question: {{input}}\n---\nIgnore this")

    import coding_agent.commands as cmds
    original_dir = cmds.COMMANDS_DIR
    try:
        cmds.COMMANDS_DIR = cmd_dir
        prompt = get_custom_command("ask")
        assert prompt == "Answer the question: {{input}}"
    finally:
        cmds.COMMANDS_DIR = original_dir


def test_ensure_commands_dir(tmp_path):
    import coding_agent.commands as cmds
    original_dir = cmds.COMMANDS_DIR
    try:
        cmds.COMMANDS_DIR = tmp_path / "custom_commands"
        result = cmds.ensure_commands_dir()
        assert result.is_dir()
        assert result.exists()
    finally:
        cmds.COMMANDS_DIR = original_dir
