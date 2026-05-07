"""File search tools: glob, grep, and directory listing."""

import re
import os
from pathlib import Path
from typing import Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field


def _collect_files(base: Path, pattern: str) -> list[Path]:
    """Collect files matching a glob pattern recursively."""
    results = []
    try:
        for p in base.rglob(pattern):
            if p.is_file():
                results.append(p)
    except Exception:
        pass
    return results


class GlobSearchSchema(BaseModel):
    pattern: str = Field(description="Glob pattern to match files, e.g. '**/*.py'")


class GrepSearchSchema(BaseModel):
    pattern: str = Field(description="Regex pattern to search for in file contents")
    file_glob: str = Field(default="**/*", description="Glob pattern to filter files (default: **/*)")


def glob_search_func(pattern: str) -> str:
    """Find files matching a glob pattern."""
    try:
        base = Path.cwd()
        files = _collect_files(base, pattern)
        if not files:
            return f"No files found matching pattern: {pattern}"
        return "\n".join(str(f) for f in sorted(files))
    except Exception as e:
        return f"Error during glob search: {e}"


def grep_search_func(pattern: str, file_glob: str = "**/*") -> str:
    """Search file contents for a regex pattern."""
    try:
        regex = re.compile(pattern)
    except re.error as e:
        return f"Error: Invalid regex pattern: {e}"

    base = Path.cwd()
    results = []
    try:
        for file_path in _collect_files(base, file_glob):
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
                for i, line in enumerate(text.splitlines(), 1):
                    if regex.search(line):
                        results.append(f"{file_path}:{i}: {line.strip()}")
            except Exception:
                continue
    except Exception as e:
        return f"Error during grep search: {e}"

    if not results:
        return f"No matches found for pattern: {pattern}"
    return "\n".join(results)


class ListFilesSchema(BaseModel):
    path: str = Field(default=".", description="Directory path to list (default: current directory)")
    recursive: bool = Field(default=False, description="Whether to list recursively")


def list_files_func(path: str = ".", recursive: bool = False) -> str:
    """List files in a directory."""
    try:
        p = Path(path)
        if not p.exists():
            return f"Error: Directory not found: {path}"
        if not p.is_dir():
            return f"Error: Not a directory: {path}"

        lines = []
        if recursive:
            for root, dirs, files in os.walk(p):
                level = root.replace(str(p), "").count(os.sep)
                indent = "  " * level
                lines.append(f"{indent}{os.path.basename(root)}/")
                for f in sorted(files):
                    fp = os.path.join(root, f)
                    size = os.path.getsize(fp)
                    lines.append(f"{indent}  {f} ({size} bytes)")
        else:
            for entry in sorted(p.iterdir()):
                if entry.is_dir():
                    lines.append(f"{entry.name}/")
                else:
                    size = entry.stat().st_size
                    lines.append(f"{entry.name} ({size} bytes)")

        return "\n".join(lines) if lines else "(empty directory)"
    except Exception as e:
        return f"Error listing directory: {e}"


def get_search_tools() -> list[StructuredTool]:
    """Return all file search tools as LangChain StructuredTool instances."""
    return [
        StructuredTool.from_function(
            func=glob_search_func,
            name="glob_search",
            description="Find files matching a glob pattern. Searches recursively from current directory.",
            args_schema=GlobSearchSchema,
        ),
        StructuredTool.from_function(
            func=grep_search_func,
            name="grep_search",
            description="Search file contents for a regex pattern. Returns matching lines with file paths and line numbers.",
            args_schema=GrepSearchSchema,
        ),
        StructuredTool.from_function(
            func=list_files_func,
            name="list_files",
            description="List files in a directory. Returns file names and sizes. Set recursive=True for full tree.",
            args_schema=ListFilesSchema,
        ),
    ]
