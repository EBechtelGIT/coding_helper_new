"""File operations tools: read, write, edit, patch."""

import json
import difflib
from pathlib import Path
from typing import Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field


class ReadFileSchema(BaseModel):
    path: str = Field(description="Path to the file to read")


class WriteFileSchema(BaseModel):
    path: str = Field(description="Path to the file to write")
    content: str = Field(description="Content to write to the file")


class EditFileSchema(BaseModel):
    path: str = Field(description="Path to the file to edit")
    old_string: str = Field(description="String to search for in the file")
    new_string: str = Field(description="String to replace old_string with")


def read_file_func(path: str) -> str:
    """Read the contents of a file."""
    try:
        content = Path(path).read_text(encoding="utf-8")
        return content
    except FileNotFoundError:
        return f"Error: File not found: {path}"
    except PermissionError:
        return f"Error: Permission denied: {path}"
    except Exception as e:
        return f"Error reading file: {e}"


def write_file_func(path: str, content: str) -> str:
    """Write content to a file (overwrites if exists)."""
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Successfully wrote to {path}"
    except PermissionError:
        return f"Error: Permission denied: {path}"
    except Exception as e:
        return f"Error writing file: {e}"


def edit_file_func(path: str, old_string: str, new_string: str) -> str:
    """Edit a file by replacing old_string with new_string."""
    try:
        p = Path(path)
        content = p.read_text(encoding="utf-8")
        if old_string not in content:
            return f"Error: old_string not found in {path}"
        new_content = content.replace(old_string, new_string)
        p.write_text(new_content, encoding="utf-8")
        return f"Successfully edited {path}"
    except FileNotFoundError:
        return f"Error: File not found: {path}"
    except Exception as e:
        return f"Error editing file: {e}"


class ApplyPatchSchema(BaseModel):
    path: str = Field(description="Path to the file to patch")
    patch: str = Field(description="Unified diff patch to apply")


def apply_patch_func(path: str, patch: str) -> str:
    """Apply a unified diff patch to a file."""
    try:
        p = Path(path)
        if not p.exists():
            return f"Error: File not found: {path}"

        original = p.read_text(encoding="utf-8").splitlines(keepends=True)
        patched = list(difflib.unified_diff(original, original, lineterm=""))

        patch_lines = patch.splitlines(True)
        applied = False

        new_content = list(original)
        i = 0
        while i < len(patch_lines):
            line = patch_lines[i]
            if line.startswith("@@ "):
                parts = line.split()
                if len(parts) >= 3:
                    old_range = parts[1]
                    old_start = int(old_range.split(",")[0].lstrip("-")) - 1

                    i += 1
                    deletions = []
                    insertions = []
                    while i < len(patch_lines):
                        pline = patch_lines[i]
                        if pline.startswith("@@") or pline.startswith("---") or pline.startswith("+++"):
                            break
                        if pline.startswith("-"):
                            deletions.append(pline[1:])
                        elif pline.startswith("+"):
                            insertions.append(pline[1:])
                        elif pline.startswith(" "):
                            insertions.append(pline[1:])
                        i += 1
                        continue
                    i += 1

                    match_idx = -1
                    for j in range(max(0, old_start - 5), min(len(new_content), old_start + len(deletions) + 5)):
                        window = [new_content[k].rstrip("\n") for k in range(j, min(j + len(deletions), len(new_content)))]
                        if window == [d.rstrip("\n") for d in deletions]:
                            match_idx = j
                            break

                    if match_idx >= 0:
                        for d in deletions:
                            new_content.pop(match_idx)
                        for idx, ins in enumerate(insertions):
                            new_content.insert(match_idx + idx, ins if ins.endswith("\n") else ins + "\n")
                        applied = True
                continue
            i += 1

        if not applied:
            return f"Error: Could not apply patch to {path}. No matching context found."

        p.write_text("".join(new_content), encoding="utf-8")
        return f"Successfully applied patch to {path}"

    except Exception as e:
        return f"Error applying patch: {e}"


def get_file_tools() -> list[StructuredTool]:
    """Return all file operation tools as LangChain StructuredTool instances."""
    return [
        StructuredTool.from_function(
            func=read_file_func,
            name="read_file",
            description="Read the contents of a file. Provide the file path.",
            args_schema=ReadFileSchema,
        ),
        StructuredTool.from_function(
            func=write_file_func,
            name="write_file",
            description="Write content to a file (overwrites if exists). Provide path and content.",
            args_schema=WriteFileSchema,
        ),
        StructuredTool.from_function(
            func=edit_file_func,
            name="edit_file",
            description="Edit a file by replacing old_string with new_string.",
            args_schema=EditFileSchema,
        ),
        StructuredTool.from_function(
            func=apply_patch_func,
            name="apply_patch",
            description="Apply a unified diff patch to a file. Safer than raw edits for complex changes.",
            args_schema=ApplyPatchSchema,
        ),
    ]
