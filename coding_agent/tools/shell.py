"""Shell execution tools - no shell=True, using subprocess with arg lists."""

import shlex
import subprocess
import sys
import os
import tempfile
from pathlib import Path
from typing import Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

import git


class RunBashSchema(BaseModel):
    command: str = Field(description="Bash command to execute")


class RunPythonSchema(BaseModel):
    code: str = Field(description="Python code to execute, or path to a .py file")


class RunGitSchema(BaseModel):
    args: str = Field(description="Git command arguments, e.g. 'status', 'diff', 'log --oneline -10'")


def _split_command(command: str) -> list[str]:
    """Split a command string into args safely (no shell interpretation)."""
    return shlex.split(command)


def run_bash_func(command: str) -> str:
    """Run a command using subprocess without shell=True.

    Pipes, redirects, and shell builtins are NOT supported for security.
    Use run_python for Python code, or chain commands explicitly.
    """
    try:
        args = _split_command(command)
        if not args:
            return "Error: Empty command"

        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = result.stdout
        if result.stderr:
            output += "\n[STDERR]\n" + result.stderr
        if result.returncode != 0:
            output += f"\n[Exit code: {result.returncode}]"
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 120 seconds"
    except FileNotFoundError:
        return f"Error: Command not found: {args[0] if args else command}"
    except Exception as e:
        return f"Error running command: {e}"


def run_python_func(code: str) -> str:
    """Run Python code using exec() or execute a .py file via subprocess."""
    code = code.strip()
    if code.endswith(".py") and os.path.isfile(code):
        try:
            result = subprocess.run(
                [sys.executable, code],
                capture_output=True,
                text=True,
                timeout=120,
            )
            output = result.stdout
            if result.stderr:
                output += "\n[STDERR]\n" + result.stderr
            if result.returncode != 0:
                output += f"\n[Exit code: {result.returncode}]"
            return output or "(no output)"
        except subprocess.TimeoutExpired:
            return "Error: Script timed out after 120 seconds"
        except Exception as e:
            return f"Error: {e}"

    try:
        import io
        import sys
        from contextlib import redirect_stdout, redirect_stderr

        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        namespace = {"__name__": "__main__"}

        try:
            compiled = compile(code, "<string>", "exec")
        except SyntaxError as e:
            return f"SyntaxError: {e}"

        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            exec(compiled, namespace)

        output = stdout_capture.getvalue()
        err = stderr_capture.getvalue()
        if err:
            output += "\n[STDERR]\n" + err
        return output or "(no output)"
    except Exception as e:
        return f"Error: {e}"


def run_git_func(args: str) -> str:
    """Run a git command using GitPython where possible, fallback to subprocess."""
    try:
        from git import Repo, GitCommandError
        repo = Repo(os.getcwd(), search_parent_directories=True)

        parts = args.split()
        if not parts:
            return "Error: Empty git command"

        cmd = parts[0]
        cmd_args = parts[1:]

        if cmd == "status":
            return repo.git.status()
        elif cmd == "log":
            fmt = cmd_args[0] if cmd_args else "--oneline"
            return repo.git.log(fmt)
        elif cmd == "diff":
            return repo.git.diff(*cmd_args)
        elif cmd == "show":
            return repo.git.show(*cmd_args)
        elif cmd == "branch":
            return repo.git.branch(*cmd_args)
        elif cmd == "add":
            repo.index.add(cmd_args or ["*"])
            return "Files staged."
        elif cmd == "commit":
            msg = ""
            rest = cmd_args
            while rest:
                if rest[0] in ("-m", "--message"):
                    if len(rest) > 1:
                        msg = rest[1]
                        rest = []
                rest = rest[1:]
            if msg:
                repo.index.commit(msg)
                return "Committed."
            return "Error: -m <message> required"
        elif cmd == "remote":
            return repo.git.remote(*cmd_args)
        else:
            return repo.git.execute(["git"] + parts)
    except ImportError:
        pass
    except Exception as e:
        return f"Git error: {e}"

    try:
        import shlex
        import subprocess
        args_list = ["git"] + shlex.split(args)
        result = subprocess.run(args_list, capture_output=True, text=True, timeout=60)
        output = result.stdout
        if result.stderr:
            output += "\n[STDERR]\n" + result.stderr
        if result.returncode != 0:
            output += f"\n[Exit code: {result.returncode}]"
        return output or "(no output)"
    except Exception as e:
        return f"Git error: {e}"


def get_shell_tools() -> list[StructuredTool]:
    """Return all shell/execution tools as LangChain StructuredTool instances.

    These tools use subprocess without shell=True for security.
    """
    return [
        StructuredTool.from_function(
            func=run_bash_func,
            name="run_bash",
            description="Run a command (no shell). Supports most programs but not pipes/redirects. "
                        "Provide the command as a string, e.g. 'ls -la' or 'python3 script.py'.",
            args_schema=RunBashSchema,
        ),
        StructuredTool.from_function(
            func=run_python_func,
            name="run_python",
            description="Run Python code. Provide inline code or a path to a .py file. "
                        "Inline code is executed via exec().",
            args_schema=RunPythonSchema,
        ),
        StructuredTool.from_function(
            func=run_git_func,
            name="run_git",
            description="Run a git command. Provide arguments without the 'git' prefix, "
                        "e.g. 'status', 'diff', 'log --oneline -5'.",
            args_schema=RunGitSchema,
        ),
    ]
