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
    patch: str = Field(description="Unified diff patch to apply. Must include @@ hunk markers with line numbers and context lines.")


def _lines_match(a: str, b: str) -> bool:
    """Compare lines, ignoring trailing whitespace differences."""
    return a.rstrip("\r\n") == b.rstrip("\r\n")


def _find_hunk_match(expected_lines: list, original_lines: list, suggested_start: int) -> int:
    """Find where a hunk's original lines match in the file.
    
    Args:
        expected_lines: Lines we expect to find (context and deletions, in order, without prefix)
        original_lines: The full file content
        suggested_start: Line number from @@ header (0-indexed)
    
    Returns:
        Index where match was found, or -1
    """
    if not expected_lines:
        return suggested_start if 0 <= suggested_start <= len(original_lines) else -1

    expected_len = len(expected_lines)
    search_window = 50

    start_search = max(0, suggested_start - search_window)
    end_search = min(len(original_lines) - expected_len + 1, suggested_start + search_window + expected_len)

    for i in range(start_search, end_search):
        match = True
        for j in range(expected_len):
            if i + j >= len(original_lines):
                match = False
                break
            if not _lines_match(expected_lines[j], original_lines[i + j]):
                match = False
                break
        if match:
            return i

    return -1


def apply_patch_func(path: str, patch: str) -> str:
    """Apply a unified diff patch to a file.
    
    The patch must be in unified diff format with:
    - @@ -start,count +start,count @@ hunk markers
    - Context lines (space prefix) for matching
    - - lines for deletions
    - + lines for insertions
    
    Example hunk:
    @@ -2,4 +2,4 @@
     context before
    -old line to delete
    +new line to insert
     context after
    """
    try:
        p = Path(path)
        if not p.exists():
            return f"Error: File not found: {path}"

        original = p.read_text(encoding="utf-8").splitlines(keepends=True)
        patch_lines = patch.splitlines(True)

        hunks = []
        i = 0

        while i < len(patch_lines):
            line = patch_lines[i]

            if line.startswith("@@ "):
                parts = line.split()
                old_start = 0
                if len(parts) >= 2:
                    old_range = parts[1]
                    old_start = int(old_range.split(",")[0].lstrip("-")) - 1

                i += 1
                
                hunk_info = {
                    "old_start": old_start,
                    "original_lines": [],  # context and deletions, in order, without prefix
                    "new_lines": [],       # context and insertions, in order, without prefix
                }

                while i < len(patch_lines):
                    pline = patch_lines[i]
                    if pline.startswith("@@") or pline.startswith("---") or pline.startswith("+++"):
                        break

                    if pline.startswith("-"):
                        hunk_info["original_lines"].append(pline[1:])
                    elif pline.startswith("+"):
                        hunk_info["new_lines"].append(pline[1:])
                    elif pline.startswith(" "):
                        hunk_info["original_lines"].append(pline[1:])
                        hunk_info["new_lines"].append(pline[1:])
                    i += 1
                    continue

                hunks.append(hunk_info)
                continue
            i += 1

        if not hunks:
            return f"Error: No valid hunks found in patch. Patch must contain @@ markers."

        new_content = list(original)
        offset = 0
        applied_hunks = 0

        for hunk in hunks:
            original_lines = hunk["original_lines"]
            new_lines = hunk["new_lines"]
            suggested_start = hunk["old_start"] + offset

            match_idx = _find_hunk_match(original_lines, new_content, suggested_start)

            if match_idx < 0:
                context_preview = "\n".join([c.rstrip() for c in original_lines[:5]])
                if len(original_lines) > 5:
                    context_preview += f"\n... and {len(original_lines) - 5} more lines"
                return (
                    f"Error: Could not apply patch to {path}. No matching context found.\n"
                    f"Suggested position: line {suggested_start + 1}\n"
                    f"Context looking for:\n{context_preview}"
                )

            for _ in range(len(original_lines)):
                if match_idx < len(new_content):
                    new_content.pop(match_idx)

            for idx, ins in enumerate(new_lines):
                line_to_insert = ins if ins.endswith("\n") else ins + "\n"
                new_content.insert(match_idx + idx, line_to_insert)

            offset += (len(new_lines) - len(original_lines))
            applied_hunks += 1

        p.write_text("".join(new_content), encoding="utf-8")
        return f"Successfully applied patch ({applied_hunks} hunk(s)) to {path}"

    except Exception as e:
        import traceback
        return f"Error applying patch: {e}\n{traceback.format_exc()}"


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
            description="""Apply a unified diff patch to a file. Best for complex multi-line changes.

IMPORTANT: Always generate VALID unified diff format:
1. Start with @@ -start,count +start,count @@
   - Example: @@ -10,5 +10,7 @@ means old lines 10-14, new lines 10-16
2. Include CONTEXT LINES (at least 1-2 unchanged lines before/after changes) with SPACE prefix
3. Use - prefix for lines to DELETE
4. Use + prefix for lines to INSERT

Example patch changing 'foo' to 'bar' with context:
@@ -2,4 +2,4 @@
 Context line before
-old content: foo
+new content: bar
 Context line after

NOTE: If the patch fails, use edit_file or write_file instead.""",
            args_schema=ApplyPatchSchema,
        ),
    ]
