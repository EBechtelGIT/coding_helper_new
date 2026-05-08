"""Plan data model and parser for the plan-build loop."""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FileChange:
    path: str
    change_type: str = "modify"  # create, modify, delete


@dataclass
class Plan:
    goal: str = ""
    current_state: str = ""
    approach: list[str] = field(default_factory=list)
    files_to_modify: list[FileChange] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    raw_text: str = ""

    def is_empty(self) -> bool:
        return not self.goal and not self.approach

    def to_prompt_block(self) -> str:
        """Format the plan for injection into another agent's context."""
        lines = ["# Approved Plan", ""]
        if self.goal:
            lines.append(f"## Goal\n{self.goal}\n")
        if self.current_state:
            lines.append(f"## Current State\n{self.current_state}\n")
        if self.approach:
            lines.append("## Approach")
            for i, step in enumerate(self.approach, 1):
                lines.append(f"  {i}. {step}")
            lines.append("")
        if self.files_to_modify:
            lines.append("## Files to Modify")
            for f in self.files_to_modify:
                lines.append(f"  - {f.change_type}: {f.path}")
            lines.append("")
        if self.risks:
            lines.append("## Risks")
            for r in self.risks:
                lines.append(f"  - {r}")
            lines.append("")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "current_state": self.current_state,
            "approach": list(self.approach),
            "files_to_modify": [{"path": f.path, "change_type": f.change_type} for f in self.files_to_modify],
            "risks": list(self.risks),
            "open_questions": list(self.open_questions),
            "raw_text": self.raw_text,
        }


_SECTION_PATTERNS = [
    (r"## Goal\s*\n(.*?)(?=\n##|\Z)", "goal"),
    (r"## Current State\s*\n(.*?)(?=\n##|\Z)", "current_state"),
    (r"## Approach\s*\n(.*?)(?=\n##|\Z)", "approach"),
    (r"## Files? to Modify\s*\n(.*?)(?=\n##|\Z)", "files"),
    (r"## Risks?\s*\n(.*?)(?=\n##|\Z)", "risks"),
    (r"## Open Questions?\s*\n(.*?)(?=\n##|\Z)", "questions"),
]

_ITEM_PATTERN = re.compile(r"^[\s]*[-*\d.]+\s+(.*)", re.MULTILINE)


def _parse_list_block(text: str) -> list[str]:
    """Parse a markdown list into items."""
    items = _ITEM_PATTERN.findall(text)
    return [item.strip() for item in items if item.strip()]


def _parse_single_block(text: str) -> str:
    """Parse a text block, stripping list markers if it's a single paragraph."""
    text = text.strip()
    if not text:
        return ""
    items = _ITEM_PATTERN.findall(text)
    if len(items) == 1:
        return items[0].strip()
    return text


def _parse_file_changes(text: str) -> list[FileChange]:
    """Parse file changes from a markdown list."""
    changes = []
    for line in text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        line = re.sub(r"^[\s]*[-*\d.]+\s+", "", line)
        change_type = "modify"
        path = line
        if ":" in line:
            parts = line.split(":", 1)
            ct = parts[0].strip().lower()
            if ct in ("create", "modify", "delete"):
                change_type = ct
                path = parts[1].strip()
        elif line.lower().startswith("create "):
            change_type = "create"
            path = line[7:].strip()
        elif line.lower().startswith("delete "):
            change_type = "delete"
            path = line[7:].strip()
        if path:
            changes.append(FileChange(path=path, change_type=change_type))
    return changes


def parse_plan_from_text(text: str) -> Plan:
    """Parse a plan from LLM markdown output."""
    plan = Plan(raw_text=text)

    for pattern, field_name in _SECTION_PATTERNS:
        match = re.search(pattern, text, re.DOTALL)
        if not match:
            continue
        content = match.group(1).strip()

        if field_name == "goal":
            plan.goal = _parse_single_block(content)
        elif field_name == "current_state":
            plan.current_state = _parse_single_block(content)
        elif field_name == "approach":
            plan.approach = _parse_list_block(content)
        elif field_name == "files":
            plan.files_to_modify = _parse_file_changes(content)
        elif field_name == "risks":
            plan.risks = _parse_list_block(content)
        elif field_name == "questions":
            plan.open_questions = _parse_list_block(content)

    return plan


def plan_from_dict(data: dict) -> Plan:
    files = [FileChange(**f) if isinstance(f, dict) else f for f in data.get("files_to_modify", [])]
    return Plan(
        goal=data.get("goal", ""),
        current_state=data.get("current_state", ""),
        approach=list(data.get("approach", [])),
        files_to_modify=files,
        risks=list(data.get("risks", [])),
        open_questions=list(data.get("open_questions", [])),
        raw_text=data.get("raw_text", ""),
    )
