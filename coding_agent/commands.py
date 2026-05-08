"""Custom commands system.

Users can define custom slash commands by placing ``.md`` files in
``.opencode/commands/<name>.md``.  When the user types ``/<name>`` the
content of that file is injected as a system-level instruction before
the agent processes the rest of the input.

If the file contains a frontmatter block (``---`` separated YAML), the
``prompt`` key is used as the command template; otherwise the entire
file content is treated as a static prompt.
"""

import re
from pathlib import Path
from typing import Optional

COMMANDS_DIR = Path(".opencode/commands")


def list_custom_commands() -> list[str]:
    """Return names (without leading ``/``) of all available custom commands."""
    if not COMMANDS_DIR.is_dir():
        return []
    return sorted(f.stem for f in COMMANDS_DIR.glob("*.md") if f.stem)


def get_custom_command(name: str) -> Optional[str]:
    """Return the prompt text for a custom ``/<name>`` command, or ``None``."""
    path = COMMANDS_DIR / f"{name}.md"
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None

    frontmatter = _parse_frontmatter(text)
    if frontmatter and "prompt" in frontmatter:
        return frontmatter["prompt"]

    return text.strip()


def _parse_frontmatter(text: str) -> Optional[dict]:
    """Parse YAML-like frontmatter from a command file.

    Only supports simple ``key: value`` pairs – complex YAML isn't needed here.
    """
    if not text.startswith("---"):
        return None
    end = text.find("---", 3)
    if end == -1:
        return None
    block = text[3:end].strip()
    result = {}
    for line in block.splitlines():
        m = re.match(r"^(\w+):\s*(.*)", line)
        if m:
            result[m.group(1)] = m.group(2).strip()
    return result if result else None


def ensure_commands_dir() -> Path:
    """Create the commands directory if it doesn't exist."""
    COMMANDS_DIR.mkdir(parents=True, exist_ok=True)
    return COMMANDS_DIR
