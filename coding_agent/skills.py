"""Skills system for the coding agent.

Skills are always-active Markdown instructions placed in ``.opencode/skills/``.
Each ``.md`` file in that directory is appended to the system prompt on every
agent invocation, so the LLM sees the instructions in every conversation turn.

Default skills are shipped with the package and copied to the project's
``.opencode/skills/`` directory on first run (when the directory does not
exist or is empty).
"""

import os
import shutil
from pathlib import Path
from typing import Optional

SKILLS_DIR = Path(".opencode/skills")
DEFAULT_SKILLS_PKG = Path(__file__).parent / "default_skills"


def load_skills(skills_dir: Optional[Path] = None) -> list[str]:
    """Return the text content of every ``.md`` file in ``skills_dir``.

    Sorted alphabetically by filename so the order is predictable.
    Returns an empty list when the directory does not exist.
    """
    directory = skills_dir or SKILLS_DIR
    if not directory.is_dir():
        return []
    contents: list[str] = []
    for md_file in sorted(directory.glob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8").strip()
            if text:
                contents.append(text)
        except OSError:
            continue
    return contents


def ensure_skills_dir(skills_dir: Optional[Path] = None) -> Path:
    """Create the skills directory and copy defaults if it is empty."""
    directory = skills_dir or SKILLS_DIR
    if directory.is_dir() and any(directory.glob("*.md")):
        return directory

    directory.mkdir(parents=True, exist_ok=True)

    # Copy default skill files shipped with the package
    if DEFAULT_SKILLS_PKG.is_dir():
        for src in DEFAULT_SKILLS_PKG.glob("*.md"):
            dst = directory / src.name
            if not dst.exists():
                shutil.copy2(str(src), str(dst))

    return directory


def get_skills_prompt(skills_dir: Optional[Path] = None) -> str:
    """Return a formatted prompt section containing all loaded skills.

    Returns an empty string when there are no skills.
    """
    skills = load_skills(skills_dir)
    if not skills:
        return ""
    sections = "\n\n".join(skills)
    return f"\n\n# Instructions\n{sections}"
