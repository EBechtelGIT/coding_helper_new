"""Tests for the tools module."""

import pytest
from pathlib import Path
import tempfile
import os

from coding_agent.tools.file_ops import get_file_tools, read_file_func, write_file_func, edit_file_func, apply_patch_func
from coding_agent.tools.file_search import get_search_tools, glob_search_func, grep_search_func
from coding_agent.tools.shell import get_shell_tools
from coding_agent.tools.web import get_web_tools
from coding_agent.tools.todo import get_todo_tools


def test_get_file_tools_returns_list():
    tools = get_file_tools()
    assert isinstance(tools, list)
    assert len(tools) == 4


def test_get_search_tools_returns_list():
    tools = get_search_tools()
    assert isinstance(tools, list)
    assert len(tools) == 3


def test_get_shell_tools_returns_list():
    tools = get_shell_tools()
    assert isinstance(tools, list)
    assert len(tools) == 3


def test_get_web_tools_returns_list():
    tools = get_web_tools()
    assert isinstance(tools, list)
    assert len(tools) == 2


def test_get_todo_tools_returns_list():
    tools = get_todo_tools()
    assert isinstance(tools, list)
    assert len(tools) == 2


def test_read_file_not_found():
    result = read_file_func(path="/nonexistent/file.txt")
    assert "Error" in result


def test_write_and_read_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.txt")
        result = write_file_func(path=path, content="Hello, World!")
        assert "Successfully" in result

        content = read_file_func(path=path)
        assert content == "Hello, World!"


def test_edit_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.txt")
        Path(path).write_text("foo bar baz")
        result = edit_file_func(
            path=path, old_string="bar", new_string="qux"
        )
        assert "Successfully" in result
        assert Path(path).read_text() == "foo qux baz"


def test_edit_file_not_found():
    result = edit_file_func(path="/nonexistent", old_string="a", new_string="b")
    assert "Error" in result


def test_glob_search():
    result = glob_search_func(pattern="*.py")
    assert isinstance(result, str)


def test_tool_names():
    all_tools = get_file_tools() + get_search_tools() + get_shell_tools() + get_web_tools() + get_todo_tools()
    tool_names = [t.name for t in all_tools]
    expected = [
        "read_file", "write_file", "edit_file", "apply_patch",
        "glob_search", "grep_search", "list_files",
        "run_bash", "run_python", "run_git",
        "web_search", "web_fetch",
        "todowrite", "todoread",
    ]
    for name in expected:
        assert name in tool_names, f"Tool '{name}' not found in tools"
