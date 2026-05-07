"""Shell, Python, and git execution tools."""

import subprocess
import tempfile
import os
from typing import Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field


class RunBashSchema(BaseModel):
    command: str = Field(description="Bash command to execute")


class RunPythonSchema(BaseModel):
    code: str = Field(description="Python code to execute, or path to a .py file")


def run_bash_func(command: str) -> str:
    """Run a bash command and return output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
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
    except Exception as e:
        return f"Error running command: {e}"


def run_python_func(code: str) -> str:
    """Run Python code or a Python script file."""
    if code.strip().endswith(".py") and os.path.isfile(code.strip()):
        script_path = code.strip()
        cmd = ["python3", script_path]
    else:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            script_path = f.name
        cmd = ["python3", script_path]

    try:
        result = subprocess.run(
            cmd,
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
        return "Error: Python script timed out after 120 seconds"
    except Exception as e:
        return f"Error running Python: {e}"
    finally:
        if not code.strip().endswith(".py"):
            try:
                os.unlink(script_path)
            except Exception:
                pass


class RunGitSchema(BaseModel):
    args: str = Field(description="Git command arguments, e.g. 'status', 'diff', 'log --oneline -10'")


def run_git_func(args: str) -> str:
    """Run a git command and return output."""
    try:
        cmd = ["git"] + args.split()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout
        if result.stderr:
            output += "\n[STDERR]\n" + result.stderr
        if result.returncode != 0:
            output += f"\n[Exit code: {result.returncode}]"
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Git command timed out after 60 seconds"
    except FileNotFoundError:
        return "Error: git is not installed or not in PATH"
    except Exception as e:
        return f"Error running git command: {e}"


def get_shell_tools() -> list[StructuredTool]:
    """Return all shell/execution tools as LangChain StructuredTool instances."""
    return [
        StructuredTool.from_function(
            func=run_bash_func,
            name="run_bash",
            description="Run a bash command and return output. Provide the command as a string.",
            args_schema=RunBashSchema,
        ),
        StructuredTool.from_function(
            func=run_python_func,
            name="run_python",
            description="Run Python code. Provide inline code or a path to a .py file.",
            args_schema=RunPythonSchema,
        ),
        StructuredTool.from_function(
            func=run_git_func,
            name="run_git",
            description="Run a git command. Provide arguments without the 'git' prefix, e.g. 'status', 'diff', 'log --oneline -5'.",
            args_schema=RunGitSchema,
        ),
    ]
